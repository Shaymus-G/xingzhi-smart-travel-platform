"""AI 聊天记录 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ai import AISessionCreate, AISessionResponse, AIChatRequest, AIChatResponse
from app.services import ai_service
from app.utils.response import success

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


# ==================== AI 对话（占位） ====================

@router.post("/chat", response_model=dict)
def chat(
    data: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI 对话接口（占位）

    后续接入 DeepSeek API 后实现真正的对话逻辑。
    当前仅保存用户消息并返回占位回复。
    """
    # 保存用户消息
    user_msg = ai_service.create_session(db, current_user.id, "user", data.message)

    # 占位回复（后续替换为 DeepSeek API 调用）
    reply_content = f"[AI 占位回复] 您好！您说的是：{data.message}。AI 对话功能开发中，敬请期待！"

    # 保存 AI 回复
    ai_msg = ai_service.create_session(db, current_user.id, "assistant", reply_content)

    return success(data={
        "session_id": user_msg.id,
        "user_message": AISessionResponse.model_validate(user_msg).model_dump(),
        "ai_message": AISessionResponse.model_validate(ai_msg).model_dump(),
    }, message="对话完成（占位模式）")
