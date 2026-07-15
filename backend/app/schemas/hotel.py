from typing import Optional
from pydantic import BaseModel, Field


class HotelCreate(BaseModel):
    """创建酒店"""
    city_id: int = Field(..., description="所属城市ID")
    name: str = Field(..., max_length=100, description="酒店名称")
    description: Optional[str] = Field(None, description="酒店描述")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    price: Optional[float] = Field(None, ge=0, description="价格")
    score: Optional[float] = Field(None, ge=0, le=5, description="评分")
    open_time: Optional[str] = Field(None, max_length=100, description="开业时间")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="纬度")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="经度")
    image_url: Optional[str] = Field(None, max_length=500, description="图片URL")


class HotelUpdate(BaseModel):
    """更新酒店"""
    city_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, ge=0)
    score: Optional[float] = Field(None, ge=0, le=5)
    open_time: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    image_url: Optional[str] = Field(None, max_length=500)


class HotelResponse(BaseModel):
    """酒店响应"""
    id: int
    city_id: int
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    price: Optional[float] = None
    score: Optional[float] = None
    open_time: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}
