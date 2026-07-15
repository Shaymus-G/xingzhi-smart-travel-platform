from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AISession(BaseModel):
    """AI聊天记录表"""
    __tablename__ = "ai_sessions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, comment="用户ID"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="角色: user/assistant/system"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="消息内容"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )

    # 关联
    user: Mapped["User"] = relationship(back_populates="ai_sessions")

    def __repr__(self) -> str:
        return f"<AISession(id={self.id}, user_id={self.user_id}, role={self.role})>"
