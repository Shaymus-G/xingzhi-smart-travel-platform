"""收藏 & 评论 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== Favorite ====================

class FavoriteCreate(BaseModel):
    """创建收藏"""
    target_type: str = Field(..., max_length=50, description="收藏目标类型: scenic_spot/hotel/restaurant")
    target_id: int = Field(..., description="收藏目标ID")


class FavoriteResponse(BaseModel):
    """收藏响应"""
    id: int
    user_id: int
    target_type: str
    target_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== Review ====================

class ReviewCreate(BaseModel):
    """创建评论"""
    target_type: str = Field(..., max_length=50, description="评论目标类型: scenic_spot/hotel/restaurant")
    target_id: int = Field(..., description="评论目标ID")
    content: str = Field(..., description="评论内容")
    score: Optional[float] = Field(None, ge=0, le=5, description="评分")


class ReviewUpdate(BaseModel):
    """更新评论"""
    content: Optional[str] = None
    score: Optional[float] = Field(None, ge=0, le=5)


class ReviewResponse(BaseModel):
    """评论响应"""
    id: int
    user_id: int
    target_type: str
    target_id: int
    content: str
    score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
