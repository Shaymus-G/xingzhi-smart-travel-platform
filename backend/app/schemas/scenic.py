from typing import Any, Optional
from pydantic import BaseModel, Field


class ScenicSpotCreate(BaseModel):
    """创建景点"""
    city_id: int = Field(..., description="所属城市ID")
    name: str = Field(..., max_length=100, description="景点名称")
    description: Optional[str] = Field(None, description="景点描述")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    category: Optional[str] = Field(None, max_length=50, description="景点类别")
    score: Optional[float] = Field(None, ge=0, le=5, description="评分")
    price: Optional[float] = Field(None, ge=0, description="门票价格")
    open_time: Optional[str] = Field(None, max_length=100, description="开放时间")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="纬度")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="经度")
    image_url: Optional[str] = Field(None, max_length=500, description="图片URL")
    tags_json: Optional[dict] = Field(None, description="标签JSON")


class ScenicSpotUpdate(BaseModel):
    """更新景点"""
    city_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)
    score: Optional[float] = Field(None, ge=0, le=5)
    price: Optional[float] = Field(None, ge=0)
    open_time: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    image_url: Optional[str] = Field(None, max_length=500)
    tags_json: Optional[dict] = None


class ScenicSpotResponse(BaseModel):
    """景点响应"""
    id: int
    city_id: int
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    score: Optional[float] = None
    price: Optional[float] = None
    open_time: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    tags_json: Optional[Any] = None

    model_config = {"from_attributes": True}
