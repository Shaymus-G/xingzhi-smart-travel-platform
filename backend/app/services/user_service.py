"""用户 & 用户偏好 Service"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.models.preference import UserPreference
from app.core.security import hash_password, verify_password


# ==================== User ====================

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """按 ID 查询用户"""
    return db.scalar(select(User).where(User.id == user_id))


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """按用户名查询用户"""
    return db.scalar(select(User).where(User.username == username))


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """按邮箱查询用户"""
    return db.scalar(select(User).where(User.email == email))


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户登录（支持用户名或邮箱）"""
    user = get_user_by_username(db, username)
    if user is None:
        user = get_user_by_email(db, username)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, username: str, email: str, password: str,
                avatar: Optional[str] = None, phone: Optional[str] = None,
                api_key: Optional[str] = None) -> User:
    """创建新用户"""
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        avatar=avatar,
        phone=phone,
        api_key=api_key,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, **kwargs) -> User:
    """更新用户信息"""
    # 特殊处理密码字段
    if "password" in kwargs and kwargs["password"] is not None:
        kwargs["password_hash"] = hash_password(kwargs.pop("password"))

    for key, value in kwargs.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """删除用户"""
    db.delete(user)
    db.commit()


def get_users(db: Session, skip: int = 0, limit: int = 20) -> list[User]:
    """分页查询用户列表"""
    stmt = select(User).offset(skip).limit(limit).order_by(User.id)
    return list(db.scalars(stmt).all())


# ==================== UserPreference ====================

def create_preference(db: Session, user_id: int, preference_type: str,
                      preference_value: str, weight: float = 1.0) -> UserPreference:
    """创建用户偏好"""
    pref = UserPreference(
        user_id=user_id,
        preference_type=preference_type,
        preference_value=preference_value,
        weight=weight,
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


def get_preference_by_id(db: Session, pref_id: int) -> Optional[UserPreference]:
    """按 ID 查询偏好"""
    return db.scalar(select(UserPreference).where(UserPreference.id == pref_id))


def get_preferences_by_user(db: Session, user_id: int) -> list[UserPreference]:
    """获取用户所有偏好"""
    stmt = select(UserPreference).where(UserPreference.user_id == user_id)
    return list(db.scalars(stmt).all())


def get_top_preferences(db: Session, user_id: int, limit: int = 10) -> list[UserPreference]:
    """获取用户 Top-N 偏好，按 weight 降序（P2 新增）"""
    stmt = (
        select(UserPreference)
        .where(UserPreference.user_id == user_id)
        .order_by(UserPreference.weight.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def delete_preference(db: Session, preference: UserPreference) -> None:
    """删除用户偏好"""
    db.delete(preference)
    db.commit()
