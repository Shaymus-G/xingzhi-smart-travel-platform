"""用户相关 API：注册 / 登录 / 个人资料 / 偏好"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse,
    UserLogin, UserLoginResponse,
    UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceResponse,
)
from app.services import user_service
from app.utils.response import success, error

router = APIRouter(prefix="/users", tags=["用户"])


# ==================== 认证相关 ====================

@router.post("/register", response_model=dict)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    if user_service.get_user_by_username(db, data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在"
        )
    # 检查邮箱是否已存在
    if user_service.get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被注册"
        )
    user = user_service.create_user(
        db,
        username=data.username,
        email=data.email,
        password=data.password,
        avatar=data.avatar,
        phone=data.phone,
        api_key=data.api_key,
    )
    return success(data=UserResponse.model_validate(user).model_dump(), message="注册成功")


@router.post("/login", response_model=dict)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = user_service.authenticate_user(db, data.username, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    token = create_access_token(user.id)
    return success(data={
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(),
    }, message="登录成功")


# ==================== 用户资料 ====================

@router.get("/me", response_model=dict)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return success(data=UserResponse.model_validate(current_user).model_dump())


@router.put("/me", response_model=dict)
def update_me(data: UserUpdate, current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """更新当前用户信息"""
    # 如果修改邮箱，检查是否已被他人使用
    if data.email and data.email != current_user.email:
        existing = user_service.get_user_by_email(db, data.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被注册"
            )
    user = user_service.update_user(db, current_user, **data.model_dump(exclude_unset=True))
    return success(data=UserResponse.model_validate(user).model_dump(), message="更新成功")


@router.get("/{user_id}", response_model=dict)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取指定用户信息"""
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return success(data=UserResponse.model_validate(user).model_dump())


# ==================== 用户偏好 ====================

@router.get("/me/preferences", response_model=dict)
def get_my_preferences(current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """获取我的偏好"""
    prefs = user_service.get_preferences_by_user(db, current_user.id)
    return success(data=[
        UserPreferenceResponse.model_validate(p).model_dump() for p in prefs
    ])


@router.post("/me/preferences", response_model=dict)
def add_preference(data: UserPreferenceCreate,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """添加偏好"""
    pref = user_service.create_preference(
        db, current_user.id, data.preference_type, data.preference_value, data.weight
    )
    return success(data=UserPreferenceResponse.model_validate(pref).model_dump(), message="偏好添加成功")


@router.delete("/me/preferences/{pref_id}", response_model=dict)
def remove_preference(pref_id: int, current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """删除偏好"""
    pref = user_service.get_preference_by_id(db, pref_id)
    if pref is None or pref.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="偏好不存在")
    user_service.delete_preference(db, pref)
    return success(message="偏好已删除")
