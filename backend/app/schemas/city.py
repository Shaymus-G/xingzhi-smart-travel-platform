from typing import Optional
from pydantic import BaseModel, Field


class CityCreate(BaseModel):
    """创建城市"""
    name: str = Field(..., max_length=100, description="城市名称")
    province: str = Field(..., max_length=50, description="省份")
    country: str = Field("中国", max_length=50, description="国家")
    description: Optional[str] = Field(None, description="城市描述")
    cover_image: Optional[str] = Field(None, max_length=500, description="封面图URL")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="纬度")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="经度")
    level: str = Field("普通", max_length=20, description="城市等级: 热门/普通/小众")


class CityUpdate(BaseModel):
    """更新城市"""
    name: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    cover_image: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    level: Optional[str] = Field(None, max_length=20)


class CityResponse(BaseModel):
    """城市响应"""
    id: int
    name: str
    province: str
    country: str
    description: Optional[str] = None
    cover_image: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    level: str

    model_config = {"from_attributes": True}
