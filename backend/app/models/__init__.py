"""
统一导入所有 ORM Model。
Alembic 会依赖这里自动发现所有数据表。
"""

from app.models.base import BaseModel
from app.models.mixins import TimestampMixin

# 所有业务 Model（按依赖顺序导入，确保 Alembic 能扫描到）
from app.models.user import User
from app.models.city import City
from app.models.scenic import ScenicSpot
from app.models.hotel import Hotel
from app.models.restaurant import Restaurant
from app.models.favorite import Favorite
from app.models.review import Review
from app.models.travel_plan import TravelPlan
from app.models.preference import UserPreference
from app.models.ai_session import AISession

__all__ = [
    "BaseModel",
    "TimestampMixin",
    "User",
    "City",
    "ScenicSpot",
    "Hotel",
    "Restaurant",
    "Favorite",
    "Review",
    "TravelPlan",
    "UserPreference",
    "AISession",
]
