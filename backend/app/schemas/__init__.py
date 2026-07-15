"""Pydantic Schemas - API 输入输出模型"""

from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserLogin, UserLoginResponse,
    UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceResponse,
)
from app.schemas.city import CityCreate, CityUpdate, CityResponse
from app.schemas.scenic import ScenicSpotCreate, ScenicSpotUpdate, ScenicSpotResponse
from app.schemas.hotel import HotelCreate, HotelUpdate, HotelResponse
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate, RestaurantResponse
from app.schemas.social import FavoriteCreate, FavoriteResponse, ReviewCreate, ReviewUpdate, ReviewResponse
from app.schemas.travel import TravelPlanCreate, TravelPlanUpdate, TravelPlanResponse
from app.schemas.ai import AISessionCreate, AISessionResponse, AIChatRequest, AIChatResponse

__all__ = [
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin", "UserLoginResponse",
    "UserPreferenceCreate", "UserPreferenceUpdate", "UserPreferenceResponse",
    "CityCreate", "CityUpdate", "CityResponse",
    "ScenicSpotCreate", "ScenicSpotUpdate", "ScenicSpotResponse",
    "HotelCreate", "HotelUpdate", "HotelResponse",
    "RestaurantCreate", "RestaurantUpdate", "RestaurantResponse",
    "FavoriteCreate", "FavoriteResponse",
    "ReviewCreate", "ReviewUpdate", "ReviewResponse",
    "TravelPlanCreate", "TravelPlanUpdate", "TravelPlanResponse",
    "AISessionCreate", "AISessionResponse", "AIChatRequest", "AIChatResponse",
]
