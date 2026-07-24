"""旅行计划结构化 Schema — Pydantic v2 模型

定义 AI 生成的旅行计划的完整结构，用于：
1. 告诉 DeepSeek 期望的输出格式
2. 验证模型输出的结构和类型
3. 传递给 plan_renderer 生成 Markdown

纯数据模型，不依赖数据库或 FastAPI。
"""

from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


# ==================== 常量 ====================

VALID_PERIODS = frozenset({"morning", "noon", "afternoon", "evening", "night"})
VALID_RESOURCE_TYPES = frozenset({"scenic_spot", "restaurant", "hotel", "general_activity", "entertainment", "shopping_mall"})

# 中英文时段映射（DeepSeek 有时输出中文）
_PERIOD_MAP = {
    "上午": "morning", "早上": "morning", "早晨": "morning",
    "中午": "noon", "下午": "afternoon",
    "傍晚": "evening", "晚上": "evening", "夜间": "night", "夜晚": "night",
}

# 中文资源类型映射
_RESOURCE_TYPE_MAP = {
    "景点": "scenic_spot", "景区": "scenic_spot", "风景区": "scenic_spot",
    "餐厅": "restaurant", "饭店": "restaurant", "美食": "restaurant", "餐饮": "restaurant",
    "酒店": "hotel", "住宿": "hotel", "宾馆": "hotel", "民宿": "hotel",
    "活动": "general_activity", "其他": "general_activity",
    "娱乐": "entertainment", "娱乐场所": "entertainment", "KTV": "entertainment", "电影院": "entertainment",
    "商场": "shopping_mall", "购物": "shopping_mall", "购物中心": "shopping_mall", "百货": "shopping_mall",
}

MAX_TIPS = 10
MAX_ASSUMPTIONS = 10
MAX_TEXT_FIELD_LENGTH = 500
MAX_ITEMS_PER_DAY = 12
MAX_MEALS_PER_DAY = 5


# ==================== 子结构 ====================


class PlanDestination(BaseModel):
    """目的地信息"""
    city_id: int = Field(..., ge=1, description="数据库城市 ID")
    name: str = Field(..., min_length=1, max_length=100, description="城市名称")
    province: str = Field(default="", max_length=50, description="省份")


class BudgetBreakdown(BaseModel):
    """预算明细 — 所有 None 自动归一化为 0.0"""
    tickets: float = Field(default=0, ge=0, description="门票费用")
    food: float = Field(default=0, ge=0, description="餐饮费用")
    lodging: float = Field(default=0, ge=0, description="住宿费用")
    transport: float = Field(default=0, ge=0, description="交通费用")
    shopping: float = Field(default=0, ge=0, description="购物费用")
    other: float = Field(default=0, ge=0, description="其他费用")

    @field_validator("tickets", "food", "lodging", "transport", "shopping", "other", mode="before")
    @classmethod
    def normalize_nullable_amount(cls, v) -> float:
        if v is None or v == "":
            return 0.0
        return v


class PlanBudget(BaseModel):
    """预算信息 — None → 0.0 自动归一化"""
    currency: str = Field(default="CNY", max_length=10)
    requested_total: Optional[float] = Field(default=None, ge=0, description="请求预算总额")
    estimated_total: float = Field(default=0, ge=0, description="预估总费用")
    breakdown: BudgetBreakdown = Field(default_factory=BudgetBreakdown)

    @field_validator("estimated_total", mode="before")
    @classmethod
    def normalize_nullable_total(cls, v) -> float:
        if v is None or v == "":
            return 0.0
        return v

    @field_validator("breakdown", mode="before")
    @classmethod
    def normalize_nullable_breakdown(cls, v):
        if v is None:
            return {}
        return v

    @field_validator("estimated_total")
    @classmethod
    def estimated_total_no_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("预估总费用不能为负数")
        return v


class ItineraryItem(BaseModel):
    """行程项目"""
    period: str = Field(..., description="时段: morning/noon/afternoon/evening/night")
    start_time: Optional[str] = Field(default=None, max_length=10, description="开始时间 HH:MM")
    end_time: Optional[str] = Field(default=None, max_length=10, description="结束时间 HH:MM")
    resource_type: str = Field(..., description="资源类型")
    resource_id: Optional[int] = Field(default=None, ge=1, description="数据库资源 ID")
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    address: Optional[str] = Field(default=None, max_length=500, description="地址")
    duration_minutes: Optional[int] = Field(default=None, ge=0, description="预计时长（分钟）")
    estimated_cost: float = Field(default=0, ge=0, description="预估费用")
    reason: Optional[str] = Field(default=None, max_length=MAX_TEXT_FIELD_LENGTH, description="选择原因")
    transport_to_next: Optional[str] = Field(default=None, max_length=MAX_TEXT_FIELD_LENGTH, description="前往下一站的交通方式")

    @field_validator("period")
    @classmethod
    def period_must_be_valid(cls, v: str) -> str:
        # 自动将中文时段转换为英文
        if v in _PERIOD_MAP:
            return _PERIOD_MAP[v]
        if v not in VALID_PERIODS:
            raise ValueError(f"无效时段: {v}，必须是 {sorted(VALID_PERIODS)} 之一")
        return v

    @field_validator("resource_type")
    @classmethod
    def resource_type_must_be_valid(cls, v: str) -> str:
        # 自动将中文资源类型转换为英文
        if v in _RESOURCE_TYPE_MAP:
            return _RESOURCE_TYPE_MAP[v]
        if v not in VALID_RESOURCE_TYPES:
            raise ValueError(f"无效资源类型: {v}，必须是 {sorted(VALID_RESOURCE_TYPES)} 之一")
        return v


class MealInfo(BaseModel):
    """用餐信息"""
    period: str = Field(..., description="用餐时段")
    resource_type: str = Field(default="restaurant")
    resource_id: Optional[int] = Field(default=None, ge=1, description="餐厅 ID")
    name: str = Field(..., min_length=1, max_length=200, description="餐厅或用餐描述")
    estimated_cost: float = Field(default=0, ge=0, description="预估费用")


class HotelInfo(BaseModel):
    """住宿信息"""
    resource_type: str = Field(default="hotel")
    resource_id: Optional[int] = Field(default=None, ge=1, description="酒店 ID")
    name: str = Field(..., min_length=1, max_length=200, description="酒店名称")
    address: Optional[str] = Field(default=None, max_length=500)
    estimated_cost: float = Field(default=0, ge=0, description="预估住宿费用")


class DayPlan(BaseModel):
    """单日行程"""
    day: int = Field(..., ge=1, description="第几天")
    theme: str = Field(default="", max_length=200, description="本日主题")
    summary: Optional[str] = Field(default=None, max_length=MAX_TEXT_FIELD_LENGTH, description="本日安排说明")
    weather_note: Optional[str] = Field(default=None, max_length=MAX_TEXT_FIELD_LENGTH, description="天气备注")
    items: list[ItineraryItem] = Field(default_factory=list, max_length=MAX_ITEMS_PER_DAY)
    meals: list[MealInfo] = Field(default_factory=list, max_length=MAX_MEALS_PER_DAY)
    hotel: Optional[HotelInfo] = Field(default=None, description="本日住宿")
    daily_estimated_cost: float = Field(default=0, ge=0, description="本日预估费用")


# ==================== 根对象 ====================


class StructuredTravelPlan(BaseModel):
    """AI 生成的完整旅行计划 — 根对象

    此 Schema 同时用于：
    - DeepSeek Prompt 中的 JSON 示例
    - 模型输出的 Pydantic 验证
    - plan_renderer 的输入
    """

    schema_version: str = Field(default="1.1", max_length=10, description="Schema 版本")
    title: str = Field(..., min_length=1, max_length=200, description="计划标题")
    destination: PlanDestination = Field(..., description="目的地信息")
    days: int = Field(..., ge=1, le=10, description="旅行天数")
    travelers: int = Field(default=1, ge=1, le=20, description="出行人数")
    summary: Optional[str] = Field(default=None, max_length=MAX_TEXT_FIELD_LENGTH, description="行程总体说明")
    budget: PlanBudget = Field(..., description="预算信息")
    itinerary: list[DayPlan] = Field(..., min_length=1, max_length=10, description="每日行程")
    tips: list[str] = Field(default_factory=list, max_length=MAX_TIPS, description="旅行贴士")
    assumptions: list[str] = Field(default_factory=list, max_length=MAX_ASSUMPTIONS, description="假设与说明")

    @field_validator("itinerary")
    @classmethod
    def itinerary_length_matches_days(cls, v: list[DayPlan], info) -> list[DayPlan]:
        """行程天数与 days 不一致时，截断或保留（不拒绝）"""
        days = info.data.get("days")
        if days is not None and len(v) > days:
            # DeepSeek 有时多生成天数，截断到请求天数
            return v[:days]
        return v

    @field_validator("itinerary")
    @classmethod
    def day_numbers_must_be_sequential(cls, v: list[DayPlan]) -> list[DayPlan]:
        """day 编号自动修正为从 1 连续递增"""
        for i, day_plan in enumerate(v, 1):
            day_plan.day = i
        return v

    def get_all_resource_ids(self) -> dict[str, set[int]]:
        """获取计划中所有引用的资源 ID，按类型分组。"""
        result: dict[str, set[int]] = {
            "scenic_spot": set(),
            "restaurant": set(),
            "hotel": set(),
            "entertainment": set(),
            "shopping_mall": set(),
        }
        for day_plan in self.itinerary:
            for item in day_plan.items:
                if item.resource_id and item.resource_type in result:
                    result[item.resource_type].add(item.resource_id)
            for meal in day_plan.meals:
                if meal.resource_id:
                    result["restaurant"].add(meal.resource_id)
            if day_plan.hotel and day_plan.hotel.resource_id:
                result["hotel"].add(day_plan.hotel.resource_id)
        return result
