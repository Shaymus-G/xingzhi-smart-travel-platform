"""AI 聊天记录 Service — 数据库层与 AI 核心包的适配器

保留现有 CRUD 能力，新增 DeepSeek 调用所需的上下文构建和回复生成。
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.ai_session import AISession
from app.core.config import Settings

from xingzhi_ai.types import ChatMessage
from xingzhi_ai.client import DeepSeekChatClient
from xingzhi_ai.context import build_messages_with_system_prompt
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
    # 数据库返回按时间倒序，调用方需逆转为正序
    return list(db.scalars(stmt).all())


def _orm_to_chat_message(msg: AISession) -> ChatMessage:
    """将 ORM 对象转换为 AI 包所需的消息格式。

    只转换 role 和 content，不传递数据库内部字段。
    """
    return ChatMessage(role=msg.role, content=msg.content)


# ==================== DeepSeek 调用 ====================


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


async def generate_ai_reply(
    db: Session,
    user_id: int,
    current_message_content: str,
    settings: Settings,
    *,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    """构建上下文并调用 DeepSeek 生成 AI 回复。

    流程：
        1. 查询当前用户最近 N 条历史消息（DB 层按时间倒序，然后逆转为正序）
        2. 转换为 AI 包需要的消息格式
        3. 构建完整上下文（system prompt + 裁剪后历史 + 当前消息）
        4. 调用 DeepSeek 客户端
        5. 返回 AI 回复文本

    Args:
        db: 数据库会话。
        user_id: 当前用户 ID。
        current_message_content: 用户当前消息内容（已保存到 DB 后传入）。
        settings: 应用配置（含 DeepSeek 参数）。
        history_limit: 最大历史消息数。
        max_context_chars: 最大上下文字符数。

    Returns:
        DeepSeek 的回复文本。

    Raises:
        AIConfigurationError: API Key 未配置。
        AIUpstreamError: DeepSeek 调用失败。
        AIEmptyResponseError: DeepSeek 返回空内容。
    """
    # 1. 查询历史消息（不含当前消息，当前消息已保存）
    recent = get_recent_messages_by_user(db, user_id, limit=history_limit)

    # 2. 恢复为时间正序（数据库查询是倒序）
    recent.reverse()

    # 3. 转换为 AI 包格式
    history: list[ChatMessage] = [_orm_to_chat_message(msg) for msg in recent]

    # 4. 当前消息
    current_msg = ChatMessage(role="user", content=current_message_content.strip())

    # 5. 构建完整上下文
    messages = build_messages_with_system_prompt(
        history=history,
        current_message=current_msg,
        max_messages=history_limit,
        max_chars=max_context_chars,
    )

    # 6. 创建客户端并调用 DeepSeek
    client = _create_client(settings)
    reply = await client.chat(messages)

    return reply
