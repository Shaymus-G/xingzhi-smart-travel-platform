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
