"""
SQLAlchemy ORM 数据模型

与 schema(1).md 中的数据库设计完全一致，共10张表。
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


class User(Base):
    """用户表 - users"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, comment="用户名")
    email = Column(String(100), nullable=False, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码")
    avatar = Column(String(255), comment="头像")
    phone = Column(String(20), comment="手机号")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    api = Column(String(50), comment="大模型API")


class City(Base):
    """城市表 - cities"""
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="城市名称")
    province = Column(String(50), comment="省份")
    country = Column(String(50), default="中国", comment="国家")
    description = Column(Text, comment="简介")
    cover_image = Column(String(255), comment="图片")
    latitude = Column(String(20), comment="纬度")
    longitude = Column(String(20), comment="经度")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联
    scenic_spots = relationship("ScenicSpot", back_populates="city")
    hotels = relationship("Hotel", back_populates="city")
    restaurants = relationship("Restaurant", back_populates="city")


class ScenicSpot(Base):
    """景点表 - scenic_spots"""
    __tablename__ = "scenic_spots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False, comment="所属城市")
    name = Column(String(100), nullable=False, comment="名称")
    description = Column(Text, comment="简介")
    address = Column(String(255), comment="地址")
    category = Column(String(50), comment="类型")
    score = Column(Float, comment="评分")
    price = Column(Float, comment="门票")
    open_time = Column(String(100), comment="开放时间")
    latitude = Column(String(20), comment="纬度")
    longitude = Column(String(20), comment="经度")
    image_url = Column(String(255), comment="图片")

    # 关联
    city = relationship("City", back_populates="scenic_spots")


class Hotel(Base):
    """酒店表 - hotels"""
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False, comment="所属城市")
    name = Column(String(100), nullable=False, comment="名称")
    description = Column(Text, comment="简介")
    address = Column(String(255), comment="地址")
    price = Column(Float, comment="价格")
    score = Column(Float, comment="评分")
    open_time = Column(String(100), comment="开业时间")
    latitude = Column(String(20), comment="纬度")
    longitude = Column(String(20), comment="经度")
    image_url = Column(String(255), comment="图片")

    # 关联
    city = relationship("City", back_populates="hotels")


class Restaurant(Base):
    """饭店表 - restaurants"""
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False, comment="所属城市")
    name = Column(String(100), nullable=False, comment="名称")
    type = Column(String(50), comment="类型")
    description = Column(Text, comment="简介")
    price_level = Column(Float, comment="价位（平均每人花销）")
    score = Column(Float, comment="评分")
    address = Column(String(255), comment="地址")
    latitude = Column(String(20), comment="纬度")
    longitude = Column(String(20), comment="经度")
    image_url = Column(String(255), comment="图片")

    # 关联
    city = relationship("City", back_populates="restaurants")


class FavoriteScenic(Base):
    """用户收藏表 - favorite_scenic"""
    __tablename__ = "favorite_scenic"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户id")
    target_type = Column(String(20), nullable=False, comment="收藏目标类型【景点、酒店还是饭店】")
    target_id = Column(Integer, nullable=False, comment="收藏目标id")
    created_at = Column(DateTime, default=datetime.now, comment="收藏时间")


class Review(Base):
    """评论表 - reviews"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户id")
    target_type = Column(String(20), nullable=False, comment="评论目标类型")
    target_id = Column(Integer, nullable=False, comment="评论目标id")
    content = Column(Text, comment="评论内容")
    score = Column(Float, comment="打分")
    created_at = Column(DateTime, default=datetime.now, comment="评论时间")


class TravelPlan(Base):
    """出行计划表 - travel_plans"""
    __tablename__ = "travel_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户id")
    title = Column(String(100), comment="标题")
    destination = Column(String(100), comment="目的地")
    days = Column(Integer, comment="出行天数")
    budget = Column(Float, comment="预算")
    plan_json = Column(JSON, comment="计划项")
    markdown = Column(Text, comment="计划内容")
    created_at = Column(DateTime, default=datetime.now, comment="计划创建时间")


class UserPreference(Base):
    """用户偏好表 - user_preference"""
    __tablename__ = "user_preference"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户")
    preference_type = Column(String(50), comment="偏好类型")
    preference_value = Column(String(255), comment="偏好内容")


class AiSession(Base):
    """AI对话记录表 - ai_sessions"""
    __tablename__ = "ai_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户id")
    role = Column(String(20), comment="AI角色")
    content = Column(Text, comment="对话内容")
    created_at = Column(DateTime, default=datetime.now, comment="保存时间")


def get_all_tables():
    """获取所有表模型类"""
    return [
        User, City, ScenicSpot, Hotel, Restaurant,
        FavoriteScenic, Review, TravelPlan, UserPreference, AiSession,
    ]