"""推荐模块 Pydantic Schema"""
from typing import Optional
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    """通用推荐请求"""
    city_id: int = Field(..., ge=1, description="当前城市 ID")
    limit: int = Field(8, ge=1, le=20, description="返回数量")


class NearbyRequest(RecommendRequest):
    radius_km: float = Field(200, ge=50, le=500, description="搜索半径（km）")


class RecommendCity(BaseModel):
    """推荐城市条目"""
    city_id: int
    city_name: str
    province: str
    level: str
    score: float
    reason: str
    cover_image: Optional[str] = None

    model_config = {"from_attributes": True}


class NearbyCity(RecommendCity):
    distance_km: float
