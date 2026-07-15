from typing import Optional
from sqlalchemy import String, Text, DECIMAL, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.mixins import TimestampMixin


class TravelPlan(BaseModel, TimestampMixin):
    """AI旅行计划表"""
    __tablename__ = "travel_plans"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, comment="用户ID"
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="计划标题"
    )
    destination: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="目的地"
    )
    days: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="旅行天数"
    )
    budget: Mapped[Optional[float]] = mapped_column(
        DECIMAL(12, 2), nullable=True, comment="预算"
    )
    plan_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="结构化行程JSON"
    )
    markdown: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="AI生成的可展示Markdown文本"
    )

    # 关联
    user: Mapped["User"] = relationship(back_populates="travel_plans")

    def __repr__(self) -> str:
        return f"<TravelPlan(id={self.id}, title={self.title})>"
