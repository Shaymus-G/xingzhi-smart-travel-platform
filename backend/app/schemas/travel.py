from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class TravelPlanCreate(BaseModel):
    """创建旅行计划"""
    title: str = Field(..., max_length=200, description="计划标题")
    destination: str = Field(..., max_length=100, description="目的地")
    days: int = Field(..., ge=1, description="旅行天数")
    budget: Optional[float] = Field(None, ge=0, description="预算")
    plan_json: Optional[dict] = Field(None, description="结构化行程JSON")
    markdown: Optional[str] = Field(None, description="AI生成的可展示Markdown文本")


class TravelPlanUpdate(BaseModel):
    """更新旅行计划"""
    title: Optional[str] = Field(None, max_length=200)
    destination: Optional[str] = Field(None, max_length=100)
    days: Optional[int] = Field(None, ge=1)
    budget: Optional[float] = Field(None, ge=0)
    plan_json: Optional[dict] = None
    markdown: Optional[str] = None


class TravelPlanResponse(BaseModel):
    """旅行计划响应"""
    id: int
    user_id: int
    title: str
    destination: str
    days: int
    budget: Optional[float] = None
    plan_json: Optional[Any] = None
    markdown: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
