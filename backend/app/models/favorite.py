from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Favorite(BaseModel):
    """收藏表"""
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, comment="用户ID"
    )
    target_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="收藏目标类型: scenic_spot/hotel/restaurant"
    )
    target_id: Mapped[int] = mapped_column(
        nullable=False, comment="收藏目标ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="收藏时间"
    )

    # 关联
    user: Mapped["User"] = relationship(back_populates="favorites")

    def __repr__(self) -> str:
        return f"<Favorite(id={self.id}, user_id={self.user_id}, target_type={self.target_type})>"
