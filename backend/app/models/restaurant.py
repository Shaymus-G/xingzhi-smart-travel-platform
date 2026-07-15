from typing import Optional
from sqlalchemy import String, Text, DECIMAL, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Restaurant(BaseModel):
    """餐厅表"""
    __tablename__ = "restaurants"

    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False, comment="所属城市ID"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="餐厅名称"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="菜系类别"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="餐厅描述"
    )
    price_level: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="价格水平"
    )
    score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 1), nullable=True, comment="评分"
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="地址"
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
    city: Mapped["City"] = relationship(back_populates="restaurants")

    def __repr__(self) -> str:
        return f"<Restaurant(id={self.id}, name={self.name})>"
