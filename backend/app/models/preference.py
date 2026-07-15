from typing import Optional
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class UserPreference(BaseModel):
    """用户偏好表"""
    __tablename__ = "user_preference"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, comment="用户ID"
    )
    preference_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="偏好类型"
    )
    preference_value: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="偏好值"
    )
    weight: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False, comment="权重"
    )

    # 关联
    user: Mapped["User"] = relationship(back_populates="preferences")

    def __repr__(self) -> str:
        return f"<UserPreference(id={self.id}, user_id={self.user_id}, type={self.preference_type})>"
