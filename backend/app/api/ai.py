"""AI 聊天记录 API"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ai import AISessionCreate, AISessionResponse, AIChatRequest
from app.services import ai_service
from app.utils.response import success
from xingzhi_ai.exceptions import (
    AIServiceError,
    AIConfigurationError,
    AIUpstreamError,
    AIEmptyResponseError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


# ==================== 聊天记录 ====================

@router.get("/sessions", response_model=dict)
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的 AI 聊天记录"""
    sessions = ai_service.get_sessions_by_user(db, current_user.id, skip=skip, limit=limit)
    return success(data=[
        AISessionResponse.model_validate(s).model_dump() for s in sessions
    ])


@router.delete("/sessions/{session_id}", response_model=dict)
def delete_session(session_id: int, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """删除聊天记录"""
    session = ai_service.get_session_by_id(db, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    ai_service.delete_session(db, session)
    return success(message="记录已删除")


# ==================== AI 对话（DeepSeek） ====================

# AI 异常 → HTTP 状态码映射
# 当前项目使用 FastAPI HTTPException，统一选择 503 表示 AI 服务不可用
# 语义：503 Service Unavailable — 上游 AI 服务暂时无法处理请求


def _handle_ai_exception(exc: AIServiceError) -> HTTPException:
    """将 AI 包异常转换为 FastAPI HTTPException。

    所有 AI 异常返回 503（上游服务不可用），
    detail 中给出用户可读的描述，不包含内部技术细节。
    """
    if isinstance(exc, AIConfigurationError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置，请联系管理员",
        )
    elif isinstance(exc, AIEmptyResponseError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务返回了无效结果，请稍后再试",
        )
    else:
        # AIUpstreamError 及其他
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务暂时不可用，请稍后再试",
        )


@router.post("/chat", response_model=dict)
async def chat(
    data: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI 对话接口 — 接入 DeepSeek API。

    当前 session_id 实际为消息 ID，仅用于兼容现有前端协议；
    真正的多会话隔离需要未来增加 conversation_id。

    处理流程:
        1. 保存用户消息
        2. 查询最近 N 条历史消息作为上下文（P1）
        3. 调用 DeepSeek 生成回复
        4. 保存 AI 回复
        5. 返回统一成功响应

    AI 调用失败时:
        - 用户消息已保存（便于排查和重试）
        - 不保存 assistant 消息
        - 返回 503 错误
    """
    # 保存用户消息（AI 调用前持久化，便于失败后排查）
    user_msg = ai_service.create_session(db, current_user.id, "user", data.message.strip())

    try:
        # 构建上下文并调用 DeepSeek
        reply_content = await ai_service.generate_ai_reply(
            db=db,
            user_id=current_user.id,
            current_message_content=data.message.strip(),
            settings=settings,
        )
    except AIServiceError as exc:
        logger.warning(
            "AI 调用失败: user_id=%d type=%s",
            current_user.id,
            type(exc).__name__,
        )
        raise _handle_ai_exception(exc)

    # 保存 AI 回复
    ai_msg = ai_service.create_session(db, current_user.id, "assistant", reply_content)

    return success(data={
        "session_id": user_msg.id,
        "user_message": AISessionResponse.model_validate(user_msg).model_dump(),
        "ai_message": AISessionResponse.model_validate(ai_msg).model_dump(),
    })
