from typing import Optional
from pydantic import BaseModel, Field


class RestaurantCreate(BaseModel):
    """创建餐厅"""
    city_id: int = Field(..., description="所属城市ID")
    name: str = Field(..., max_length=100, description="餐厅名称")
    category: Optional[str] = Field(None, max_length=50, description="菜系类别")
    description: Optional[str] = Field(None, description="餐厅描述")
    price_level: Optional[str] = Field(None, max_length=20, description="价格水平")
    score: Optional[float] = Field(None, ge=0, le=5, description="评分")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="纬度")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="经度")
    image_url: Optional[str] = Field(None, max_length=500, description="图片URL")


class RestaurantUpdate(BaseModel):
    """更新餐厅"""
    city_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    price_level: Optional[str] = Field(None, max_length=20)
    score: Optional[float] = Field(None, ge=0, le=5)
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    image_url: Optional[str] = Field(None, max_length=500)


class RestaurantResponse(BaseModel):
    """餐厅响应"""
    id: int
    city_id: int
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price_level: Optional[str] = None
    score: Optional[float] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}
