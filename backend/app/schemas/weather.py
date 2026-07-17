"""天气模块 Pydantic Schema"""
from typing import Optional
from pydantic import BaseModel, Field


class WeatherQuery(BaseModel):
    """天气查询参数"""
    city: str = Field(..., description="城市名称，如：杭州")
    days: int = Field(7, ge=3, le=7, description="预报天数（3 或 7）")
