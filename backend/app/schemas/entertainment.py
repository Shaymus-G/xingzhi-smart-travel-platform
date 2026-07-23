"""娱乐场所 Schema"""
from typing import Optional
from pydantic import BaseModel, Field


class EntertainmentCreate(BaseModel):
    city_id: int = Field(..., description="所属城市ID")
    name: str = Field(..., max_length=100, description="名称")
    description: Optional[str] = Field(None, description="简介")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    category: Optional[str] = Field(None, max_length=50, description="类型")
    score: Optional[float] = Field(None, ge=0, le=5)
    price: Optional[float] = Field(None, ge=0)
    open_time: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    image_url: Optional[str] = Field(None, max_length=500)


class EntertainmentUpdate(BaseModel):
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


class EntertainmentResponse(BaseModel):
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

    model_config = {"from_attributes": True}
