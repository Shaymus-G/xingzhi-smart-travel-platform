from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ==================== User ====================

class UserCreate(BaseModel):
    """创建用户"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码（明文）")
    avatar: Optional[str] = Field(None, max_length=500, description="头像URL")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    api_key: Optional[str] = Field(None, max_length=255, description="用户自己的大模型API Key")


class UserUpdate(BaseModel):
    """更新用户（所有字段可选）"""
    username: Optional[str] = Field(None, min_length=2, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: Optional[str] = Field(None, min_length=6, max_length=128, description="新密码（明文）")
    avatar: Optional[str] = Field(None, max_length=500, description="头像URL")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    api_key: Optional[str] = Field(None, max_length=255, description="用户自己的大模型API Key")
    is_active: Optional[bool] = Field(None, description="是否激活")


class UserResponse(BaseModel):
    """用户响应（不含密码哈希）"""
    id: int
    username: str
    email: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    api_key: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """用户登录"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserLoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==================== UserPreference ====================

class UserPreferenceCreate(BaseModel):
    """创建用户偏好"""
    preference_type: str = Field(..., max_length=50, description="偏好类型")
    preference_value: str = Field(..., max_length=255, description="偏好值")
    weight: float = Field(1.0, ge=0, description="权重")


class UserPreferenceUpdate(BaseModel):
    """更新用户偏好"""
    preference_type: Optional[str] = Field(None, max_length=50)
    preference_value: Optional[str] = Field(None, max_length=255)
    weight: Optional[float] = Field(None, ge=0)


class UserPreferenceResponse(BaseModel):
    """用户偏好响应"""
    id: int
    user_id: int
    preference_type: str
    preference_value: str
    weight: float

    model_config = {"from_attributes": True}
