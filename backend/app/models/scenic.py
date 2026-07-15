from typing import Optional
from sqlalchemy import String, Text, DECIMAL, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ScenicSpot(BaseModel):
    """景点表"""
    __tablename__ = "scenic_spots"

    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False, comment="所属城市ID"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="景点名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="景点描述"
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="地址"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="景点类别"
    )
    score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 1), nullable=True, comment="评分"
    )
    price: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2), nullable=True, comment="门票价格"
    )
    open_time: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="开放时间"
    )
    latitude: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 7), nullable=True, comment="纬度"
    )
    longitude: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 7), nullable=True, comment="经度"
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="图片URL"
    )
    tags_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="标签JSON, 用于AI推荐"
    )

    # 关联
    city: Mapped["City"] = relationship(back_populates="scenic_spots")

    def __repr__(self) -> str:
        return f"<ScenicSpot(id={self.id}, name={self.name})>"
