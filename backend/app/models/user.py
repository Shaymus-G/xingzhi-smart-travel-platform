from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.mixins import TimestampMixin


class User(BaseModel, TimestampMixin):
    """用户表"""
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="邮箱"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希"
    )
    avatar: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="头像URL"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="手机号"
    )
    api_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="用户自己的大模型API Key"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否激活"
    )

    # 关联
    favorites: Mapped[List["Favorite"]] = relationship(back_populates="user")
    reviews: Mapped[List["Review"]] = relationship(back_populates="user")
    travel_plans: Mapped[List["TravelPlan"]] = relationship(back_populates="user")
    preferences: Mapped[List["UserPreference"]] = relationship(back_populates="user")
    ai_sessions: Mapped[List["AISession"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
