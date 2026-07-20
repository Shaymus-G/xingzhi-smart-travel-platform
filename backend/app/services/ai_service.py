"""AI 聊天记录 Service — 数据库层与 AI 核心包的适配器

P1：保留现有 CRUD 能力，新增 DeepSeek 调用所需的上下文构建和回复生成。
P2：整合真实旅游数据、用户偏好和天气信息增强 AI 上下文。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.ai_session import AISession
from app.core.config import Settings

from xingzhi_ai.types import ChatMessage
from xingzhi_ai.client import DeepSeekChatClient
from xingzhi_ai.context import build_messages_with_system_prompt, build_messages_with_travel_context
from xingzhi_ai.location import (
    CityCandidate,
    find_mentioned_city,
    resolve_city_from_conversation,
    resolve_weather_city_name,
)
from xingzhi_ai.travel_context import (
    ScenicInfo,
    HotelInfo,
    RestaurantInfo,
    PreferenceInfo,
    WeatherInfo,
    TravelContext,
    build_travel_context_block,
)
from xingzhi_ai.exceptions import (
    AIServiceError,
    AIConfigurationError,
    AIUpstreamError,
    AIEmptyResponseError,
)

logger = logging.getLogger(__name__)

# 多轮上下文默认上限
DEFAULT_HISTORY_LIMIT = 20
DEFAULT_MAX_CONTEXT_CHARS = 8000

# P2 旅游资源默认候选数量
DEFAULT_TOP_SCENICS = 8
DEFAULT_TOP_HOTELS = 5
DEFAULT_TOP_RESTAURANTS = 5
DEFAULT_TOP_PREFERENCES = 10


# ==================== 现有 CRUD（保留） ====================


def get_session_by_id(db: Session, session_id: int) -> Optional[AISession]:
    """按 ID 查询聊天记录"""
    return db.scalar(select(AISession).where(AISession.id == session_id))


def get_sessions_by_user(
    db: Session, user_id: int, skip: int = 0, limit: int = 50
) -> list[AISession]:
    """获取用户的聊天记录（按创建时间正序）"""
    stmt = (
        select(AISession)
        .where(AISession.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(AISession.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def create_session(
    db: Session, user_id: int, role: str, content: str
) -> AISession:
    """创建聊天记录（立即提交）"""
    session = AISession(user_id=user_id, role=role, content=content)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session: AISession) -> None:
    """删除聊天记录"""
    db.delete(session)
    db.commit()


# ==================== 多轮上下文查询 ====================


def get_recent_messages_by_user(
    db: Session,
    user_id: int,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[AISession]:
    """获取当前用户最近 N 条消息。

    数据库层先按 created_at DESC 取最新 N 条（性能优化），
    调用方需要按时间正序排列后传给 AI。

    Args:
        db: 数据库会话。
        user_id: 当前用户 ID（确保不会读到其他用户）。
        limit: 最大消息数量。

    Returns:
        按 created_at DESC 排列的消息列表（调用方需反转）。
    """
    stmt = (
        select(AISession)
        .where(AISession.user_id == user_id)
        .order_by(desc(AISession.created_at), desc(AISession.id))
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def _orm_to_chat_message(msg: AISession) -> ChatMessage:
    """将 ORM 对象转换为 AI 包所需的消息格式。

    只转换 role 和 content，不传递数据库内部字段。
    """
    return ChatMessage(role=msg.role, content=msg.content)


# ==================== DeepSeek 客户端 ====================


def _create_client(settings: Settings) -> DeepSeekChatClient:
    """创建 DeepSeekChatClient 实例。

    每次请求新建轻量包装对象。底层 AsyncOpenAI 的 HTTP 连接复用
    由 httpx 连接池管理，不需要应用层缓存。
    """
    return DeepSeekChatClient(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
        timeout_seconds=settings.DEEPSEEK_TIMEOUT_SECONDS,
    )


# ==================== P2 ORM → 普通数据转换 ====================


def _orm_scenic_to_dict(spot) -> dict:
    """ScenicSpot ORM → 普通 dict（安全序列化，含 ID 供 P3 计划引用）"""
    tags = ""
    if getattr(spot, "tags_json", None) and isinstance(spot.tags_json, dict):
        tags = ", ".join(str(v) for v in spot.tags_json.values())
    return {
        "id": spot.id,
        "name": spot.name,
        "category": getattr(spot, "category", "") or "",
        "score": float(spot.score) if getattr(spot, "score", None) is not None else None,
        "price": float(spot.price) if getattr(spot, "price", None) is not None else None,
        "open_time": getattr(spot, "open_time", "") or "",
        "tags": tags,
        "address": getattr(spot, "address", "") or "",
        "description": getattr(spot, "description", "") or "",
    }


def _orm_hotel_to_dict(hotel) -> dict:
    """Hotel ORM → 普通 dict（含 ID 供 P3 计划引用）"""
    return {
        "id": hotel.id,
        "name": hotel.name,
        "score": float(hotel.score) if getattr(hotel, "score", None) is not None else None,
        "price": float(hotel.price) if getattr(hotel, "price", None) is not None else None,
        "address": getattr(hotel, "address", "") or "",
        "description": getattr(hotel, "description", "") or "",
    }


def _orm_restaurant_to_dict(restaurant) -> dict:
    """Restaurant ORM → 普通 dict（含 ID 供 P3 计划引用）"""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "category": getattr(restaurant, "category", "") or "",
        "score": float(restaurant.score) if getattr(restaurant, "score", None) is not None else None,
        "price_level": getattr(restaurant, "price_level", "") or "",
        "address": getattr(restaurant, "address", "") or "",
        "description": getattr(restaurant, "description", "") or "",
    }


def _orm_preference_to_dict(pref) -> dict:
    """UserPreference ORM → 普通 dict"""
    return {
        "preference_type": pref.preference_type,
        "preference_value": pref.preference_value,
        "weight": float(getattr(pref, "weight", 1.0)),
    }


# ==================== P2 天气触发判断 ====================


# 触发天气查询的关键词
_WEATHER_TRIGGER_KEYWORDS = frozenset({
    "天气", "下雨", "晴天", "阴天", "温度", "气温", "冷", "热",
    "穿衣", "带伞", "防晒", "户外", "爬山", "徒步", "海边",
    "行程", "出游", "一日游", "几日游", "几天", "出行",
    "推荐", "安排", "计划", "攻略", "路线",
})


def _should_query_weather(user_text: str, settings: Settings) -> bool:
    """判断是否应触发天气查询。

    条件：
    1. OPENWEATHER_KEY 已配置；
    2. 用户消息包含天气/出行相关关键词。

    注意：城市识别失败时不会调用此函数。
    """
    if not settings.OPENWEATHER_KEY:
        return False
    text_lower = user_text.lower()
    return any(kw in text_lower for kw in _WEATHER_TRIGGER_KEYWORDS)


# ==================== P2 增强回复生成 ====================


async def generate_ai_reply(
    db: Session,
    user_id: int,
    current_message_content: str,
    settings: Settings,
    *,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    """构建上下文并调用 DeepSeek 生成 AI 回复（P2 增强版）。

    P2 流程：
        1. 查询当前用户最近 N 条历史消息
        2. 获取全部城市候选列表
        3. 多轮城市解析：优先当前消息 → 倒序历史 user 消息继承
        4. 识别成功 → 查询 Top-N 旅游资源
        5. 查询用户偏好
        6. 条件性查询天气（仅当前消息触发，使用归一化城市名）
        7. 构建 TravelContext + 数据块
        8. 使用增强上下文调用 DeepSeek
        9. 返回 AI 回复文本

    多轮目的地继承：
        - 当前消息明确提到新城市 → 覆盖历史城市
        - 当前消息无城市 → 从最近 user 消息倒序查找
        - assistant 消息中的城市不参与匹配
        - 始终无城市 → 退化为 P1 模式

    所有增强步骤失败时安全降级。

    Args:
        db: 数据库会话。
        user_id: 当前用户 ID。
        current_message_content: 用户当前消息内容。
        settings: 应用配置。
        history_limit: 最大历史消息数。
        max_context_chars: 最大上下文字符数。

    Returns:
        DeepSeek 的回复文本。

    Raises:
        AIConfigurationError: API Key 未配置。
        AIUpstreamError: DeepSeek 调用失败。
        AIEmptyResponseError: DeepSeek 返回空内容。
    """
    from app.services import travel_service, user_service, weather_service

    # 1. 查询历史消息
    recent = get_recent_messages_by_user(db, user_id, limit=history_limit)
    recent.reverse()  # 恢复为时间正序
    history: list[ChatMessage] = [_orm_to_chat_message(msg) for msg in recent]
    current_msg = ChatMessage(role="user", content=current_message_content.strip())

    # 2. 提取历史 user 消息文本（用于多轮城市继承）
    previous_user_messages: list[str] = [
        m["content"] for m in history if m.get("role") == "user"
    ]

    # 3. 尝试识别/继承城市
    travel_context_block = ""
    try:
        all_cities = travel_service.get_all_cities(db)
        city_candidates = [
            CityCandidate(
                name=city.name,
                province=city.province or "",
                city_id=city.id,
            )
            for city in all_cities
        ]
        # P2 多轮：优先当前消息，其次从历史 user 消息倒序继承
        matched_city = resolve_city_from_conversation(
            current_message=current_message_content,
            recent_user_messages=previous_user_messages,
            city_candidates=city_candidates,
        )
    except Exception:
        logger.warning("城市候选列表查询失败", exc_info=True)
        matched_city = None

    # 4. 如果城市识别成功，收集旅游数据
    if matched_city is not None:
        city_id = matched_city.city_id
        province = matched_city.province
        # 天气查询和 Prompt 显示使用用户友好的城市名
        display_city_name = resolve_weather_city_name(matched_city)

        logger.info(
            "P2 城市解析成功: user_id=%d city=%s display=%s city_id=%d",
            user_id, matched_city.name, display_city_name, city_id,
        )

        # 4a. 查询旅游资源（每类独立 try/except）
        scenics: list[dict] = []
        hotels: list[dict] = []
        restaurants: list[dict] = []
        preferences: list[dict] = []
        weather_dict: Optional[dict] = None

        try:
            scenic_orms = travel_service.get_top_scenics_by_city(
                db, city_id, limit=DEFAULT_TOP_SCENICS
            )
            scenics = [_orm_scenic_to_dict(s) for s in scenic_orms]
        except Exception:
            logger.warning("景点查询失败: city_id=%d", city_id, exc_info=True)

        try:
            hotel_orms = travel_service.get_top_hotels_by_city(
                db, city_id, limit=DEFAULT_TOP_HOTELS
            )
            hotels = [_orm_hotel_to_dict(h) for h in hotel_orms]
        except Exception:
            logger.warning("酒店查询失败: city_id=%d", city_id, exc_info=True)

        try:
            restaurant_orms = travel_service.get_top_restaurants_by_city(
                db, city_id, limit=DEFAULT_TOP_RESTAURANTS
            )
            restaurants = [_orm_restaurant_to_dict(r) for r in restaurant_orms]
        except Exception:
            logger.warning("餐厅查询失败: city_id=%d", city_id, exc_info=True)

        # 4b. 用户偏好
        try:
            pref_orms = user_service.get_top_preferences(
                db, user_id, limit=DEFAULT_TOP_PREFERENCES
            )
            preferences = [_orm_preference_to_dict(p) for p in pref_orms]
        except Exception:
            logger.warning("用户偏好查询失败: user_id=%d", user_id, exc_info=True)

        # 4c. 天气（条件性查询：当前消息触发 + 城市已知）
        if _should_query_weather(current_message_content, settings):
            try:
                weather_result = await weather_service.get_current_weather(
                    db, display_city_name
                )
                if "error" not in weather_result:
                    weather_dict = {
                        "city": weather_result.get("city", display_city_name),
                        "temperature": weather_result.get("temperature", ""),
                        "feels_like": weather_result.get("feels_like", ""),
                        "weather": weather_result.get("weather", ""),
                        "humidity": weather_result.get("humidity", ""),
                        "wind_speed": weather_result.get("wind_speed", ""),
                        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    }
                    logger.info("天气查询成功: city=%s", display_city_name)
                else:
                    logger.warning(
                        "天气查询返回错误: city=%s error=%s",
                        display_city_name, weather_result.get("error"),
                    )
            except Exception:
                logger.warning(
                    "天气查询异常: city=%s", display_city_name, exc_info=True
                )

        # 4d. 构建 TravelContext（使用用户友好的城市名）
        travel_ctx = TravelContext(
            city_name=display_city_name,
            province=province,
            scenics=tuple(ScenicInfo.from_dict(s) for s in scenics),
            hotels=tuple(HotelInfo.from_dict(h) for h in hotels),
            restaurants=tuple(RestaurantInfo.from_dict(r) for r in restaurants),
            preferences=tuple(PreferenceInfo.from_dict(p) for p in preferences),
            weather=WeatherInfo.from_dict(weather_dict) if weather_dict else None,
        )

        # 4e. 构建旅游数据块
        travel_context_block = build_travel_context_block(travel_ctx)

        logger.info(
            "P2 旅游上下文构建完成: city=%s scenics=%d hotels=%d restaurants=%d "
            "preferences=%d weather=%s block_chars=%d",
            display_city_name,
            len(scenics),
            len(hotels),
            len(restaurants),
            len(preferences),
            "yes" if weather_dict else "no",
            len(travel_context_block),
        )
    else:
        logger.info("P2 城市未解析: user_id=%d，退化为 P1 模式", user_id)

    # 4. 构建最终 messages
    if travel_context_block.strip():
        messages = build_messages_with_travel_context(
            history=history,
            current_message=current_msg,
            travel_context_block=travel_context_block,
            max_messages=history_limit,
            max_chars=max_context_chars,
        )
    else:
        # P1 降级路径
        messages = build_messages_with_system_prompt(
            history=history,
            current_message=current_msg,
            max_messages=history_limit,
            max_chars=max_context_chars,
        )

    # 5. 调用 DeepSeek
    client = _create_client(settings)
    reply = await client.chat(messages)

    return reply
