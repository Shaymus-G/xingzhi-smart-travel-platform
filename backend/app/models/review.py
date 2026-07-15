from typing import Optional
from sqlalchemy import String, Text, DECIMAL, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.mixins import TimestampMixin


class Review(BaseModel, TimestampMixin):
    """评论表"""
    __tablename__ = "reviews"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, comment="用户ID"
    )
    target_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="评论目标类型: scenic_spot/hotel/restaurant"
    )
    target_id: Mapped[int] = mapped_column(
        nullable=False, comment="评论目标ID"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="评论内容"
    )
    score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 1), nullable=True, comment="评分"
    )

    # 关联
    user: Mapped["User"] = relationship(back_populates="reviews")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, user_id={self.user_id}, target_type={self.target_type})>"
