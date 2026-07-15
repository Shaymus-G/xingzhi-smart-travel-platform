from typing import Optional
from sqlalchemy import String, Text, DECIMAL, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Hotel(BaseModel):
    """酒店表"""
    __tablename__ = "hotels"

    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False, comment="所属城市ID"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="酒店名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="酒店描述"
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="地址"
    )
    price: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2), nullable=True, comment="价格"
    )
    score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 1), nullable=True, comment="评分"
    )
    open_time: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="开业时间"
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

    # 关联
    city: Mapped["City"] = relationship(back_populates="hotels")

    def __repr__(self) -> str:
        return f"<Hotel(id={self.id}, name={self.name})>"
