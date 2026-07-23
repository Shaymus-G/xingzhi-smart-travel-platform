"""娱乐场所 Model"""
from typing import Optional
from sqlalchemy import String, Text, DECIMAL, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Entertainment(BaseModel):
    """娱乐场所表（KTV/电影院/酒吧/网吧等）"""
    __tablename__ = "entertainments"

    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False, comment="所属城市ID"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="简介"
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="详细地址"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="类型（KTV/电影院/酒吧/网吧等）"
    )
    score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 1), nullable=True, comment="评分"
    )
    price: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2), nullable=True, comment="参考价格"
    )
    open_time: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="营业时间"
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

    city: Mapped["City"] = relationship(back_populates="entertainments")

    def __repr__(self) -> str:
        return f"<Entertainment(id={self.id}, name={self.name})>"
