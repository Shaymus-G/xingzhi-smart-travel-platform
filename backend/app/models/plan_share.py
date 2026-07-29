"""旅行计划分享表"""
import uuid
import hashlib
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


def _generate_share_token() -> str:
    return uuid.uuid4().hex


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class PlanShare(BaseModel):
    __tablename__ = "plan_shares"

    plan_id: Mapped[int] = mapped_column(ForeignKey("travel_plans.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, comment="脱敏后的计划快照 JSON")
    include_budget: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active / revoked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan = relationship("TravelPlan")
