"""AI 旅行计划生成 Service — P3 核心编排

职责：
- 目的地匹配与城市解析
- 旅游资源查询（复用 P2 函数）
- 用户偏好查询
- 可选天气查询
- 构建计划生成 Prompt
- 调用 DeepSeek（使用 response_format json_object）
- JSON 解析与 Pydantic 验证
- 业务资源引用验证
- Markdown 确定性渲染
- 保存 TravelPlan 到数据库

不负责：HTTP 路由、JWT 认证、请求 Schema 验证（由 API 层处理）
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.travel_plan import TravelPlan

from xingzhi_ai.client import DeepSeekChatClient
from xingzhi_ai.location import (
    CityCandidate,
    find_mentioned_city,
    resolve_weather_city_name,
)
from xingzhi_ai.plan_schema import StructuredTravelPlan
from xingzhi_ai.plan_parser import extract_and_parse_json, PlanParseError
from xingzhi_ai.plan_validation import validate_plan_resources, ValidationResult
from xingzhi_ai.plan_renderer import render_travel_plan_markdown
from xingzhi_ai.plan_prompts import build_plan_system_prompt
from xingzhi_ai.travel_context import build_travel_context_block, TravelContext
from xingzhi_ai.travel_context import (
    ScenicInfo,
    HotelInfo,
    RestaurantInfo,
    PreferenceInfo,
    WeatherInfo,
    filter_and_rank_entertainments,
    filter_and_rank_malls,
)
from xingzhi_ai.exceptions import (
    AIServiceError,
    AIUpstreamError,
    AIEmptyResponseError,
)

logger = logging.getLogger(__name__)

# P3 候选数量（根据天数动态调整）
_MIN_SCENICS = 8
_MIN_HOTELS = 5
_MIN_RESTAURANTS = 5
_MAX_SCENICS = 24
_MAX_HOTELS = 10
_MAX_RESTAURANTS = 16
_MIN_ENTERTAINMENTS = 3
_MAX_ENTERTAINMENTS = 8
_MIN_MALLS = 3
_MAX_MALLS = 8
_MAX_PREFERENCES = 10


class PlanGenerationError(Exception):
    """计划生成失败 — 用户可读消息"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ==================== 主编排函数 ====================


async def generate_travel_plan(
    db: Session,
    user_id: int,
    destination: str,
    days: int,
    settings: Settings,
    *,
    budget: Optional[float] = None,
    travelers: int = 1,
    preferences: Optional[list[str]] = None,
    start_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> TravelPlan:
    """生成旅行计划并持久化到数据库。

    完整流程：
    1. 匹配目的地城市
    2. 查询候选旅游资源
    3. 查询用户偏好
    4. 可选天气查询
    5. 构建 Prompt
    6. 调用 DeepSeek（response_format json_object）
    7. 解析 JSON → Pydantic 验证
    8. 业务资源引用验证
    9. 确定性生成 Markdown
    10. 写入数据库 → 返回

    Raises:
        PlanGenerationError: 目的地不存在、解析失败、验证失败。
        AIUpstreamError: DeepSeek 调用失败。
        AIEmptyResponseError: DeepSeek 返回空内容。
    """
    from app.services import travel_service, user_service, weather_service

    # ==================== 1. 匹配目的地 ====================
    all_cities = travel_service.get_all_cities(db)
    city_candidates = [
        CityCandidate(name=city.name, province=city.province or "", city_id=city.id)
        for city in all_cities
    ]
    # 先尝试原始名称精确匹配，再尝试归一化
    matched_city = None
    # 精确查找
    city_orm = travel_service.get_city_by_name(db, destination)
    if city_orm:
        matched_city = CityCandidate(
            name=city_orm.name,
            province=city_orm.province or "",
            city_id=city_orm.id,
        )
    else:
        # 模糊匹配
        matched_city = find_mentioned_city(destination, city_candidates)

    if matched_city is None:
        raise PlanGenerationError(f"平台中未找到该目的地城市「{destination}」")

    city_id = matched_city.city_id
    display_name = resolve_weather_city_name(matched_city)
    province = matched_city.province

    logger.info(
        "P3 目的地匹配: user_id=%d destination=%s → city=%s city_id=%d",
        user_id, destination, display_name, city_id,
    )

    # ==================== 2. 查询候选资源 ====================
    scenic_limit = min(max(days * 4, _MIN_SCENICS), _MAX_SCENICS)
    hotel_limit = min(max(days, _MIN_HOTELS), _MAX_HOTELS)
    restaurant_limit = min(max(days * 2, _MIN_RESTAURANTS), _MAX_RESTAURANTS)

    scenics: list[dict] = []
    hotels: list[dict] = []
    restaurants: list[dict] = []
    preferences_data: list[dict] = []
    weather_dict: Optional[dict] = None

    try:
        from app.services.ai_service import _orm_scenic_to_dict
        scenic_orms = travel_service.get_top_scenics_by_city(db, city_id, limit=scenic_limit)
        scenics = [_orm_scenic_to_dict(s) for s in scenic_orms]
    except Exception:
        logger.warning("P3 景点查询失败: city_id=%d", city_id, exc_info=True)

    try:
        from app.services.ai_service import _orm_hotel_to_dict
        hotel_orms = travel_service.get_top_hotels_by_city(db, city_id, limit=hotel_limit)
        hotels = [_orm_hotel_to_dict(h) for h in hotel_orms]
    except Exception:
        logger.warning("P3 酒店查询失败: city_id=%d", city_id, exc_info=True)

    try:
        from app.services.ai_service import _orm_restaurant_to_dict
        restaurant_orms = travel_service.get_top_restaurants_by_city(db, city_id, limit=restaurant_limit)
        restaurants = [_orm_restaurant_to_dict(r) for r in restaurant_orms]
    except Exception:
        logger.warning("P3 餐厅查询失败: city_id=%d", city_id, exc_info=True)

    # Entertainment & ShoppingMall (P4 + P5 语义评分)
    entertainment_limit = min(max(days, _MIN_ENTERTAINMENTS), _MAX_ENTERTAINMENTS)
    mall_limit = min(max(days, _MIN_MALLS), _MAX_MALLS)

    entertainments: list[dict] = []
    malls: list[dict] = []

    try:
        from app.services.ai_service import _orm_entertainment_to_dict
        ent_orms = travel_service.get_top_entertainments_by_city(
            db, city_id, limit=entertainment_limit * 2
        )
        raw_ents = [_orm_entertainment_to_dict(e) for e in ent_orms]
        entertainments = filter_and_rank_entertainments(
            raw_ents,
            preferences=preferences,
            notes=notes or "",
            max_count=entertainment_limit,
        )
    except Exception:
        logger.warning("P3 娱乐查询失败: city_id=%d", city_id, exc_info=True)

    try:
        from app.services.ai_service import _orm_mall_to_dict
        mall_orms = travel_service.get_top_malls_by_city(
            db, city_id, limit=mall_limit * 2
        )
        raw_malls = [_orm_mall_to_dict(m) for m in mall_orms]
        malls = filter_and_rank_malls(
            raw_malls,
            preferences=preferences,
            notes=notes or "",
            max_count=mall_limit,
        )
    except Exception:
        logger.warning("P3 商场查询失败: city_id=%d", city_id, exc_info=True)

    # ==================== 3. 用户偏好 ====================
    try:
        pref_orms = user_service.get_top_preferences(db, user_id, limit=_MAX_PREFERENCES)
        from app.services.ai_service import _orm_preference_to_dict
        preferences_data = [_orm_preference_to_dict(p) for p in pref_orms]
    except Exception:
        logger.warning("P3 偏好查询失败: user_id=%d", user_id, exc_info=True)

    # ==================== 4. 候选资源 ID 映射（供验证使用） ====================
    scenic_by_id: dict[int, dict] = {}
    for s in scenics:
        sid = s.get("id")
        if sid:
            scenic_by_id[int(sid)] = s

    hotel_by_id: dict[int, dict] = {}
    for h in hotels:
        hid = h.get("id")
        if hid:
            hotel_by_id[int(hid)] = h

    restaurant_by_id: dict[int, dict] = {}
    for r in restaurants:
        rid = r.get("id")
        if rid:
            restaurant_by_id[int(rid)] = r

    entertainment_by_id: dict[int, dict] = {}
    for e in entertainments:
        eid = e.get("id")
        if eid:
            entertainment_by_id[int(eid)] = e

    mall_by_id: dict[int, dict] = {}
    for m in malls:
        mid = m.get("id")
        if mid:
            mall_by_id[int(mid)] = m

    # ==================== 5. 构建基础旅游上下文（不用于 Prompt，用于日志） ====================
    # 这里不用 P2 的完整 TravelContext，而是直接构建精简的候选数据
    _candidate_count = f"scenics={len(scenics)} hotels={len(hotels)} restaurants={len(restaurants)}"
    logger.info("P3 候选资源: %s preferences=%d", _candidate_count, len(preferences_data))

    # ==================== 6. 构建 Prompt ====================
    system_prompt = build_plan_system_prompt()

    # 用户消息：包含请求参数 + 候选资源数据
    user_message = _build_plan_user_message(
        destination_name=display_name,
        province=province,
        city_id=city_id,
        days=days,
        budget=budget,
        travelers=travelers,
        preferences=preferences,
        start_date=start_date,
        notes=notes,
        scenics=scenics,
        hotels=hotels,
        restaurants=restaurants,
        entertainments=entertainments,
        malls=malls,
        history_preferences=preferences_data,
    )

    # ==================== 7. 调用 DeepSeek ====================
    client = _create_plan_client(settings)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # 动态 max_tokens：每天约 2000 tokens，底线 4000，上限 16000
    plan_max_tokens = min(max(days * 2000, 4000), 16000)

    logger.info(
        "P3 调用 DeepSeek: user_id=%d days=%d budget=%s max_tokens=%d",
        user_id, days, budget, plan_max_tokens,
    )

    try:
        raw_response = await client.chat(
            messages,
            temperature=0.2,
            max_tokens=plan_max_tokens,
            response_format={"type": "json_object"},
        )
    except (AIUpstreamError, AIEmptyResponseError):
        raise
    except AIServiceError as e:
        raise PlanGenerationError(f"AI 服务错误: {e.message}")

    logger.info("P3 DeepSeek 响应: %d chars", len(raw_response))

    # ==================== 8. 解析 JSON ====================
    try:
        plan_dict = extract_and_parse_json(raw_response)
    except PlanParseError as e:
        logger.warning("P3 JSON 解析失败: %s", e.message[:200])
        raise PlanGenerationError("AI 生成的旅行计划格式无效，请稍后重试")

    # ==================== 9. Pydantic 验证 ====================
    try:
        plan = StructuredTravelPlan.model_validate(plan_dict)
    except Exception as e:
        import json as _json
        from pydantic import ValidationError
        if isinstance(e, ValidationError):
            errors = e.errors(include_url=False)
            logger.warning(
                "P3 Pydantic 验证失败: count=%d errors=%s",
                len(errors),
                _json.dumps(errors, ensure_ascii=False, default=str)[:5000],
            )
        else:
            logger.warning("P3 Pydantic 验证失败: %s", str(e)[:500])
        raise PlanGenerationError("AI 生成的旅行计划格式无效，请稍后重试")

    # ==================== 10. 业务验证 ====================
    validation = validate_plan_resources(
        plan,
        matched_city_id=city_id,
        matched_city_name=display_name,
        matched_province=province,
        requested_days=days,
        scenic_candidates=scenic_by_id,
        hotel_candidates=hotel_by_id,
        restaurant_candidates=restaurant_by_id,
        entertainment_candidates=entertainment_by_id,
        mall_candidates=mall_by_id,
    )

    if not validation.is_valid:
        logger.warning(
            "P3 业务验证失败: %d errors — %s",
            len(validation.errors),
            "; ".join(validation.errors[:5]),
        )
        raise PlanGenerationError("AI 生成的旅行计划格式无效，请稍后重试")

    if validation.warnings:
        logger.warning("P3 业务验证警告: %s", "; ".join(validation.warnings[:5]))

    # 使用标准化后的计划
    final_plan = validation.normalized_plan or plan

    # ==================== 11. 补全真实交通（P5 新增） ====================
    await _fill_real_transport(
        final_plan,
        db=db,
        city_id=city_id,
        city_name=display_name,
        user_preferences=preferences,
    )

    # ==================== 11.5 地点坐标绑定（同名消歧 + GCJ-02 回填） ====================
    try:
        from app.services.location_binder import bind_plan_locations
        plan_dict_before = final_plan.model_dump()
        plan_dict_after = bind_plan_locations(plan_dict_before, city_id, db)
        final_plan = StructuredTravelPlan.model_validate(plan_dict_after)
        logger.info("P3 地点绑定完成: city_id=%d", city_id)
    except Exception:
        logger.warning("P3 地点绑定失败: city_id=%d", city_id, exc_info=True)

    # ==================== 12. 渲染 Markdown ====================
    markdown = render_travel_plan_markdown(final_plan)

    # ==================== 13. 写入数据库 ====================
    try:
        travel_plan = travel_service.create_plan(
            db,
            user_id=user_id,
            title=final_plan.title,
            destination=display_name,
            days=final_plan.days,
            budget=budget,
            plan_json=final_plan.model_dump(),
            markdown=markdown,
        )
        logger.info(
            "P3 计划已保存: plan_id=%d user_id=%d title=%s",
            travel_plan.id, user_id, final_plan.title,
        )
        return travel_plan
    except Exception as e:
        logger.error("P3 数据库保存失败: %s", str(e)[:200])
        raise PlanGenerationError("旅行计划保存失败，请稍后再试")


# ==================== 辅助函数 ====================


def _create_plan_client(settings: Settings) -> DeepSeekChatClient:
    """创建 DeepSeek 客户端（复用现有封装）"""
    return DeepSeekChatClient(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
        timeout_seconds=settings.DEEPSEEK_TIMEOUT_SECONDS,
    )


def _build_plan_user_message(
    destination_name: str,
    province: str,
    city_id: int,
    days: int,
    budget: Optional[float],
    travelers: int,
    preferences: Optional[list[str]],
    start_date: Optional[str],
    notes: Optional[str],
    scenics: list[dict],
    hotels: list[dict],
    restaurants: list[dict],
    entertainments: list[dict],
    malls: list[dict],
    history_preferences: list[dict],
) -> str:
    """构建发送给 DeepSeek 的用户消息（包含候选资源数据）"""
    lines: list[str] = []
    lines.append("请根据以下信息和平台数据，生成一个结构化的旅行计划 JSON。")
    lines.append("")
    lines.append("## 请求参数")
    lines.append(f"- 目的地：{destination_name}（城市ID: {city_id}，省份: {province}）")
    lines.append(f"- 天数：{days} 天")
    if budget:
        lines.append(f"- 预算：¥{budget:.0f}")
    if travelers > 1:
        lines.append(f"- 人数：{travelers} 人")
    if preferences:
        lines.append(f"- 本次偏好：{', '.join(preferences)}")
    if start_date:
        lines.append(f"- 出行日期：{start_date}")
    if notes:
        lines.append(f"- 补充要求：{notes}")
    lines.append("")

    # 候选景点（含 ID）
    if scenics:
        lines.append("## 候选景点")
        lines.append("")
        for i, s in enumerate(scenics, 1):
            lines.append(_format_scenic_line(i, s))
        lines.append("")

    # 候选酒店（含 ID）
    if hotels:
        lines.append("## 候选酒店")
        lines.append("")
        for i, h in enumerate(hotels, 1):
            lines.append(_format_hotel_line(i, h))
        lines.append("")

    # 候选餐厅（含 ID）
    if restaurants:
        lines.append("## 候选餐厅")
        lines.append("")
        for i, r in enumerate(restaurants, 1):
            lines.append(_format_restaurant_line(i, r))
        lines.append("")

    # 候选娱乐资源
    if entertainments:
        lines.append("## 候选娱乐资源")
        lines.append("")
        for i, e in enumerate(entertainments, 1):
            lines.append(_format_entertainment_line(i, e))
        lines.append("")

    # 候选商场
    if malls:
        lines.append("## 候选商场")
        lines.append("")
        for i, m in enumerate(malls, 1):
            lines.append(_format_mall_line(i, m))
        lines.append("")

    # 历史偏好
    if history_preferences:
        lines.append("## 用户历史偏好")
        for p in history_preferences:
            lines.append(
                f"- {p.get('preference_type', '')}：{p.get('preference_value', '')}"
                f"（权重 {p.get('weight', 1.0):.1f}）"
            )
        lines.append("")

    # 重要提醒
    lines.append("## 重要提醒")
    lines.append("1. 只输出一个 JSON 对象，不要包含任何解释或 Markdown 格式")
    lines.append("2. 景点、酒店、餐厅的 resource_id 必须使用上述候选列表中提供的实际 ID")
    lines.append("3. 每条候选数据的第一行包含真实 ID，请使用该 ID")
    lines.append("4. 请输出一个有效的 JSON 对象（json）")

    return "\n".join(lines)


def _format_scenic_line(index: int, s: dict) -> str:
    """格式化候选景点行（包含数据库 ID）"""
    sid = s.get("id", "?")
    name = s.get("name", "?")
    score = s.get("score")
    score_str = f"{score:.1f}" if score else "N/A"
    price = s.get("price")
    if price is None:
        price_str = "N/A"
    elif price == 0:
        price_str = "Free"
    else:
        price_str = f"Y{price:.0f}"
    category = s.get("category", "")
    addr = s.get("address", "")
    desc = (s.get("description", "") or "")[:150]
    tags = s.get("tags", "")
    open_time = s.get("open_time", "")
    lines = [f"{index}. [ID:{sid}] {name}"]
    if category:
        lines.append(f"   Category: {category}")
    lines.append(f"   Score: {score_str} | Ticket: {price_str}")
    if open_time:
        lines.append(f"   Hours: {open_time}")
    if tags:
        lines.append(f"   Tags: {tags}")
    if addr:
        lines.append(f"   Address: {addr}")
    if desc:
        lines.append(f"   Description: {desc}")
    return "\n".join(lines)


def _format_hotel_line(index: int, h: dict) -> str:
    """格式化候选酒店行（包含数据库 ID）"""
    hid = h.get("id", "?")
    name = h.get("name", "?")
    score = h.get("score")
    score_str = f"{score:.1f}" if score else "N/A"
    price = h.get("price")
    price_str = f"Y{price:.0f}" if price else "N/A"
    addr = h.get("address", "")
    desc = (h.get("description", "") or "")[:100]
    lines = [f"{index}. [ID:{hid}] {name}"]
    lines.append(f"   Score: {score_str} | Price: {price_str}")
    if addr:
        lines.append(f"   Address: {addr}")
    if desc:
        lines.append(f"   Description: {desc}")
    return "\n".join(lines)


def _format_restaurant_line(index: int, r: dict) -> str:
    """格式化候选餐厅行（包含数据库 ID）"""
    rid = r.get("id", "?")
    name = r.get("name", "?")
    score = r.get("score")
    score_str = f"{score:.1f}" if score else "N/A"
    category = r.get("category", "")
    price_level = r.get("price_level", "")
    addr = r.get("address", "")
    desc = (r.get("description", "") or "")[:100]
    lines = [f"{index}. [ID:{rid}] {name}"]
    if category:
        lines.append(f"   Cuisine: {category}")
    lines.append(f"   Score: {score_str} | Level: {price_level or 'N/A'}")
    if addr:
        lines.append(f"   Address: {addr}")
    if desc:
        lines.append(f"   Description: {desc}")
    return "\n".join(lines)


def _format_entertainment_line(index: int, e: dict) -> str:
    """格式化候选娱乐行（包含数据库 ID）"""
    eid = e.get("id", "?")
    name = e.get("name", "?")
    score = e.get("score")
    score_str = f"{score:.1f}" if score else "N/A"
    price = e.get("price")
    price_str = f"Y{price:.0f}" if price else "N/A"
    category = e.get("category", "")
    open_time = e.get("open_time", "")
    lines = [f"{index}. [ID:{eid}] {name}"]
    if category:
        lines.append(f"   Category: {category}")
    lines.append(f"   Score: {score_str} | Price: {price_str}")
    if open_time:
        lines.append(f"   Hours: {open_time}")
    return "\n".join(lines)


def _format_mall_line(index: int, m: dict) -> str:
    """格式化候选商场行（包含数据库 ID）"""
    mid = m.get("id", "?")
    name = m.get("name", "?")
    score = m.get("score")
    score_str = f"{score:.1f}" if score else "N/A"
    category = m.get("category", "")
    open_time = m.get("open_time", "")
    lines = [f"{index}. [ID:{mid}] {name}"]
    if category:
        lines.append(f"   Category: {category}")
    lines.append(f"   Score: {score_str}")
    if open_time:
        lines.append(f"   Hours: {open_time}")
    return "\n".join(lines)


# ==================== 真实交通补全（P5 新增） ====================

# Haversine 距离阈值（米）
_WALK_DISTANCE_M = 1500       # ≤1500m → 步行
_BIKE_MAX_DISTANCE_M = 5000   # 1500-5000m → 骑行或公交
# >5000m → 公交

# 调用上限
_MAX_TRANSIT_PER_DAY = 3
_MAX_TRANSIT_TOTAL = 8

# 可导航资源类型
_NAVIGABLE_TYPES = frozenset({"scenic_spot", "restaurant", "hotel", "entertainment", "shopping_mall"})


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间的 Haversine 直线距离（米）。

    纯函数，可独立测试。
    """
    R = 6371000  # 地球半径（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _choose_transit_method(
    distance_m: float,
    user_preferences: list[str] | None,
) -> str:
    """根据距离和用户偏好选择出行方式。

    优先级：
    1. 用户 notes/preferences 中明确要求 → 优先采用
    2. ≤1500m → walking
    3. 1500-5000m → bicycling（降级为 transit）
    4. >5000m → transit

    Returns:
        "walking" | "bicycling" | "transit" | "driving"
    """
    pref_text = " ".join(p.lower() for p in (user_preferences or []))

    # 从 preferences 中检测出行方式偏好
    if any(kw in pref_text for kw in ("自驾", "开车", "驾车", "自己开车")):
        return "driving"
    if any(kw in pref_text for kw in ("骑行", "单车", "自行车", "骑车")):
        return "bicycling"
    if any(kw in pref_text for kw in ("步行", "走路", "徒步")):
        return "walking"

    # 默认根据距离选择
    if distance_m <= _WALK_DISTANCE_M:
        return "walking"
    elif distance_m <= _BIKE_MAX_DISTANCE_M:
        return "bicycling"
    else:
        return "transit"


def _safe_scalar(value) -> float | None:
    """安全提取数值标量。

    处理：数字、合法数字字符串、空列表、None、空字符串。
    返回 None 表示无法提取。
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    if isinstance(value, (list, dict)):
        return None
    return None


def _format_distance(distance_value) -> str | None:
    """安全格式化距离。

    兼容：纯数字（米）、纯数字字符串、已含单位的字符串（如 "12832 米"）。
    """
    # 已是带单位的字符串 → 直接返回
    if isinstance(distance_value, str) and distance_value.strip():
        s = distance_value.strip()
        if any(u in s for u in ("米", "公里", "千米", "km", "KM")):
            return s
    # 纯数字
    s = _safe_scalar(distance_value)
    if s is None:
        return None
    if s >= 1000:
        return f"{s/1000:.1f} 公里"
    return f"{int(s)} 米"


def _format_duration(duration_value) -> str | None:
    """安全格式化时长。

    兼容：纯数字（分钟）、纯数字字符串、已含单位的字符串（如 "45 分钟"）。
    """
    # 已是带单位的字符串 → 直接返回
    if isinstance(duration_value, str) and duration_value.strip():
        s = duration_value.strip()
        if any(u in s for u in ("分钟", "小时", "min", "Min")):
            return s
    # 纯数字
    s = _safe_scalar(duration_value)
    if s is None:
        return None
    minutes = int(s)
    if minutes >= 60:
        h = minutes // 60
        m = minutes % 60
        return f"{h} 小时{m} 分钟" if m else f"{h} 小时"
    return f"{minutes} 分钟"


def _format_transit_string(result: dict) -> str | None:
    """将 transit_service 返回的结果格式化为稳定的字符串。

    不输出 Python repr、完整原始 JSON、None、coroutine。
    安全处理空数组、None、空字符串、缺失字段。

    Returns:
        格式化的交通描述字符串，或 None（无法格式化时）。
    """
    if not result or "error" in result:
        return None

    method = result.get("method", "")
    dist_str = _format_distance(result.get("distance"))
    dur_str = _format_duration(result.get("duration"))

    if method == "transit":
        # 无公交方案：distance/duration 为空 → 返回降级文本
        if dist_str is None and dur_str is None:
            return "暂未获取到可用的公共交通路线，请以地图实时查询结果为准"

        parts: list[str] = []
        if dur_str and dist_str:
            parts.append(f"公交/地铁约 {dur_str}，约 {dist_str}")
        elif dur_str:
            parts.append(f"公交/地铁约 {dur_str}")
        elif dist_str:
            parts.append(f"公交/地铁约 {dist_str}")

        cost = result.get("cost")
        cost_scalar = _safe_scalar(cost)
        if cost_scalar is not None and cost_scalar > 0:
            parts.append(f"，票价约 {cost_scalar:.0f} 元")
        elif isinstance(cost, str) and cost.strip():
            # 已含单位的字符串（如 "4.0 元"）
            parts.append(f"，票价约 {cost.strip()}")

        walking = _safe_scalar(result.get("walking_distance"))
        if walking is not None and walking > 0:
            parts.append(f"，含步行约 {int(walking)} 米")

        # 提取关键换乘
        segments = result.get("segments", [])
        if isinstance(segments, list):
            key_steps: list[str] = []
            for seg in segments[:6]:
                if not isinstance(seg, dict):
                    continue
                seg_type = seg.get("type", "")
                if seg_type in ("subway", "bus"):
                    name = seg.get("name", "")
                    departure = seg.get("departure", "")
                    arrival = seg.get("arrival", "")
                    if name and departure and arrival:
                        key_steps.append(f"{departure}乘{name}至{arrival}")
                    elif name:
                        key_steps.append(str(name))
            if key_steps:
                parts.append("；" + "，".join(key_steps[:3]))

        parts.append("；请以出行时地图实时结果为准")
        return "".join(parts)

    elif method == "driving":
        if dist_str is None and dur_str is None:
            return "驾车路线暂未获取到，请以地图实时查询结果为准"
        parts = [f"驾车约 {dur_str or '未知'}，约 {dist_str or '未知'}"]
        toll = result.get("toll")
        if toll and not isinstance(toll, (list, dict)):
            toll_str = str(toll).strip()
            if toll_str:
                parts.append(f"，预计过路费 {toll_str}")
        lights = _safe_scalar(result.get("traffic_lights"))
        if lights is not None and lights > 0:
            parts.append(f"，约 {int(lights)} 个红绿灯")
        return "".join(parts)

    elif method == "walking":
        if dist_str and dur_str:
            return f"步行约 {dur_str}，约 {dist_str}"
        return "步行路线暂未获取到"

    elif method == "bicycling":
        if dist_str and dur_str:
            return f"骑行约 {dur_str}，约 {dist_str}"
        return "骑行路线暂未获取到"


async def _fill_real_transport(
    plan,
    *,
    db,
    city_id: int,
    city_name: str,
    user_preferences: list[str] | None,
) -> None:
    """为验证后的计划补全真实交通信息。

    构建统一时间线（items + meals + hotel），按 period 排序后
    对相邻可导航资源调用 transit_service 获取真实路线，
    将结果写入 ItineraryItem.transport_to_next（原地修改 plan）。

    限制：
    - 每天最多 3 段
    - 全计划最多 8 段
    - general_activity / resource_id=None → 跳过
    - 相同 from/to/method → 局部缓存
    - 只有 ItineraryItem 可写入 transport_to_next
    - 任何失败 → 保留模型已有描述或填入通用降级文本

    Args:
        plan: 已验证的 StructuredTravelPlan（会被原地修改）。
        db: 数据库会话。
        city_id: 城市 ID。
        city_name: 城市名（公交模式需要）。
        user_preferences: 用户偏好列表。
    """
    from app.services import transit_service, travel_service

    try:
        from app.core.config import settings as app_settings
        if not app_settings.AMAP_KEY:
            logger.info("P3 交通: AMAP_KEY 未配置，跳过 Transit 补全")
            return
    except Exception:
        logger.info("P3 交通: 无法读取 AMAP_KEY，跳过 Transit 补全")
        return

    # 时段排序权重（morning < noon < afternoon < evening < night）
    _PERIOD_ORDER = {"morning": 0, "noon": 1, "afternoon": 2, "evening": 3, "night": 4}

    # resource_id → (lat, lng) 的坐标缓存
    coord_cache: dict[tuple[str, int], tuple[float, float] | None] = {}
    # (from_type, from_id, to_type, to_id, method) → formatted_string 的结果缓存
    result_cache: dict[tuple, str | None] = {}

    total_filled = 0

    def _get_coords(res_type: str, res_id: int) -> tuple[float, float] | None:
        """获取资源经纬度（带缓存）"""
        key = (res_type, res_id)
        if key in coord_cache:
            return coord_cache[key]

        try:
            if res_type == "scenic_spot":
                r = travel_service.get_scenic_by_id(db, res_id)
            elif res_type == "hotel":
                r = travel_service.get_hotel_by_id(db, res_id)
            elif res_type == "restaurant":
                r = travel_service.get_restaurant_by_id(db, res_id)
            elif res_type == "entertainment":
                r = travel_service.get_entertainment_by_id(db, res_id)
            elif res_type == "shopping_mall":
                r = travel_service.get_mall_by_id(db, res_id)
            else:
                coord_cache[key] = None
                return None

            if r and r.latitude and r.longitude:
                result = (float(r.latitude), float(r.longitude))
            else:
                result = None
        except Exception:
            result = None

        coord_cache[key] = result
        return result

    for day_plan in plan.itinerary:
        if total_filled >= _MAX_TRANSIT_TOTAL:
            break

        day_filled = 0

        # ========== 构建统一时间线 ==========
        # 每个节点: (period_order, resource_type, resource_id, source_object, kind)
        # kind ∈ {"item", "meal", "hotel"}
        # 只有 kind="item" 的节点可写入 transport_to_next
        timeline: list[dict] = []

        for item in day_plan.items:
            order = _PERIOD_ORDER.get(item.period, 2)
            timeline.append({
                "order": order,
                "res_type": item.resource_type,
                "res_id": item.resource_id,
                "source": item,
                "kind": "item",
            })

        for meal in day_plan.meals:
            order = _PERIOD_ORDER.get(meal.period, 1)
            timeline.append({
                "order": order,
                "res_type": meal.resource_type or "restaurant",
                "res_id": meal.resource_id,
                "source": meal,
                "kind": "meal",
            })

        if day_plan.hotel and day_plan.hotel.resource_id:
            timeline.append({
                "order": 5,  # hotel 总是在最后
                "res_type": "hotel",
                "res_id": day_plan.hotel.resource_id,
                "source": day_plan.hotel,
                "kind": "hotel",
            })

        # 按 period 排序
        timeline.sort(key=lambda n: n["order"])

        # ========== 为相邻节点补全交通 ==========
        for i in range(len(timeline) - 1):
            if total_filled >= _MAX_TRANSIT_TOTAL or day_filled >= _MAX_TRANSIT_PER_DAY:
                break

            from_node = timeline[i]
            to_node = timeline[i + 1]

            # 只有 ItineraryItem 有 transport_to_next 字段
            if from_node["kind"] != "item":
                continue

            from_type = from_node["res_type"]
            from_id = from_node["res_id"]
            to_type = to_node["res_type"]
            to_id = to_node["res_id"]

            # 跳过不可导航资源
            if not from_id or from_type not in _NAVIGABLE_TYPES:
                continue
            if not to_id or to_type not in _NAVIGABLE_TYPES:
                continue

            # 同一资源跳过
            if (from_type, from_id) == (to_type, to_id):
                continue

            # 获取坐标
            from_coords = _get_coords(from_type, from_id)
            to_coords = _get_coords(to_type, to_id)

            if not from_coords or not to_coords:
                continue

            # Haversine 距离 → 选择方式
            dist_m = _haversine_distance_m(
                from_coords[0], from_coords[1],
                to_coords[0], to_coords[1],
            )
            method = _choose_transit_method(dist_m, user_preferences)

            # 查缓存
            cache_key = (from_type, from_id, to_type, to_id, method)
            if cache_key in result_cache:
                transport_str = result_cache[cache_key]
            else:
                try:
                    transit_result = await transit_service.get_route(
                        db, from_type, from_id, to_type, to_id, method, city_name,
                    )
                    transport_str = _format_transit_string(transit_result)
                except Exception:
                    logger.warning(
                        "P3 Transit 调用失败: from=(%s,%d) to=(%s,%d) method=%s",
                        from_type, from_id, to_type, to_id, method,
                        exc_info=True,
                    )
                    transport_str = None
                result_cache[cache_key] = transport_str

            # 写入 transport_to_next（from_node["source"] 是 ItineraryItem）
            target_item = from_node["source"]
            if transport_str:
                target_item.transport_to_next = transport_str
                day_filled += 1
                total_filled += 1
            else:
                # 降级：保留模型已有描述或写入通用提示
                if not target_item.transport_to_next:
                    target_item.transport_to_next = "建议使用地图软件查询实时路线"

    if total_filled > 0:
        logger.info(
            "P3 Transit 补全完成: total_filled=%d/%d",
            total_filled, _MAX_TRANSIT_TOTAL,
        )
    else:
        logger.info("P3 Transit: 无符合条件的相邻资源对，跳过补全")
