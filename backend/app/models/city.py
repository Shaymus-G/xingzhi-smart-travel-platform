from typing import Optional, List
from sqlalchemy import String, Text, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class City(BaseModel):
    """城市表"""
    __tablename__ = "cities"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="城市名称"
    )
    province: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="省份"
    )
    country: Mapped[str] = mapped_column(
        String(50), default="中国", nullable=False, comment="国家"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="城市描述"
    )
    cover_image: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="封面图URL"
    )
    latitude: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 7), nullable=True, comment="纬度"
    )
    longitude: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 7), nullable=True, comment="经度"
    )
    level: Mapped[str] = mapped_column(
        String(20), default="普通", nullable=False, comment="城市等级: 热门/普通/小众"
    )

    # 关联
    scenic_spots: Mapped[List["ScenicSpot"]] = relationship(back_populates="city")
    hotels: Mapped[List["Hotel"]] = relationship(back_populates="city")
    restaurants: Mapped[List["Restaurant"]] = relationship(back_populates="city")
    entertainments: Mapped[List["Entertainment"]] = relationship(back_populates="city")
    shopping_malls: Mapped[List["ShoppingMall"]] = relationship(back_populates="city")

    def __repr__(self) -> str:
        return f"<City(id={self.id}, name={self.name})>"
