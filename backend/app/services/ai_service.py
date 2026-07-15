"""AI 聊天记录 Service"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.ai_session import AISession


def get_session_by_id(db: Session, session_id: int) -> Optional[AISession]:
    """按 ID 查询聊天记录"""
    return db.scalar(select(AISession).where(AISession.id == session_id))


def get_sessions_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> list[AISession]:
    """获取用户的聊天记录"""
    stmt = select(AISession).where(AISession.user_id == user_id)
    stmt = stmt.offset(skip).limit(limit).order_by(AISession.created_at.asc())
    return list(db.scalars(stmt).all())


def create_session(db: Session, user_id: int, role: str, content: str) -> AISession:
    """创建聊天记录"""
    session = AISession(user_id=user_id, role=role, content=content)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session: AISession) -> None:
    """删除聊天记录"""
    db.delete(session)
    db.commit()
