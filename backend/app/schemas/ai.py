from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class AISessionCreate(BaseModel):
    """创建AI聊天记录"""
    role: str = Field(..., max_length=20, description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class AISessionResponse(BaseModel):
    """AI聊天记录响应"""
    id: int
    user_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AIChatRequest(BaseModel):
    """AI对话请求"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="用户消息",
    )
    session_id: int | None = Field(
        None,
        description="会话ID，仅用于前端协议兼容，后端当前按最近N条消息构建上下文",
    )

    @field_validator("message")
    @classmethod
    def validate_message_not_blank(cls, v: str) -> str:
        """拒绝纯空格消息（min_length=1 无法过滤纯空格）"""
        if not v.strip():
            raise ValueError("消息不能为空")
        return v


class AIChatResponse(BaseModel):
    """AI 对话响应 — 与 API 实际返回结构一致"""
    session_id: int
    user_message: AISessionResponse
    ai_message: AISessionResponse


# ==================== P3: 旅行计划生成 ====================


class PlanGenerateRequest(BaseModel):
    """AI 旅行计划生成请求"""

    destination: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="目的地城市名称（如：杭州）",
    )
    days: int = Field(..., ge=1, le=10, description="旅行天数（1-10）")
    budget: float | None = Field(None, ge=0, description="预算总额（人民币元）")
    travelers: int = Field(default=1, ge=1, le=20, description="出行人数")
    preferences: list[str] | None = Field(
        default=None, max_length=10, description="本次行程偏好（最多 10 条）"
    )
    start_date: str | None = Field(default=None, description="出行日期（YYYY-MM-DD）")
    notes: str | None = Field(default=None, max_length=1000, description="补充要求")

    @field_validator("destination")
    @classmethod
    def destination_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("目的地不能为空")
        return v.strip()

    @field_validator("preferences")
    @classmethod
    def preferences_strip(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        stripped = [p.strip() for p in v if p.strip()]
        if not stripped:
            return None
        if len(stripped) > 10:
            raise ValueError("偏好最多 10 条")
        return stripped
