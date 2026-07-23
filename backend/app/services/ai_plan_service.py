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

    # Entertainment & ShoppingMall (P4)
    entertainment_limit = min(max(days, _MIN_ENTERTAINMENTS), _MAX_ENTERTAINMENTS)
    mall_limit = min(max(days, _MIN_MALLS), _MAX_MALLS)

    entertainments: list[dict] = []
    malls: list[dict] = []

    try:
        from app.services.ai_service import _orm_entertainment_to_dict
        ent_orms = travel_service.get_top_entertainments_by_city(db, city_id, limit=entertainment_limit)
        entertainments = [_orm_entertainment_to_dict(e) for e in ent_orms]
    except Exception:
        logger.warning("P3 娱乐查询失败: city_id=%d", city_id, exc_info=True)

    try:
        from app.services.ai_service import _orm_mall_to_dict
        mall_orms = travel_service.get_top_malls_by_city(db, city_id, limit=mall_limit)
        malls = [_orm_mall_to_dict(m) for m in mall_orms]
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

    logger.info("P3 调用 DeepSeek: user_id=%d days=%d budget=%s", user_id, days, budget)

    try:
        raw_response = await client.chat(messages, temperature=0.7)
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
        logger.warning("P3 Pydantic 验证失败: %s", str(e)[:300])
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

    # ==================== 11. 渲染 Markdown ====================
    markdown = render_travel_plan_markdown(final_plan)

    # ==================== 12. 写入数据库 ====================
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
