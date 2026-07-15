from datetime import datetime
from pydantic import BaseModel, Field


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
    message: str = Field(..., description="用户消息")
    session_id: int | None = Field(None, description="会话ID，用于多轮对话")


class AIChatResponse(BaseModel):
    """AI对话响应"""
    session_id: int
    reply: str
