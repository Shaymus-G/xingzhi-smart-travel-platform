"""旅游资源 Service：城市 / 景点 / 酒店 / 餐厅 / 旅行计划"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.city import City
from app.models.scenic import ScenicSpot
from app.models.hotel import Hotel
from app.models.restaurant import Restaurant
from app.models.travel_plan import TravelPlan


# ==================== City ====================

def get_city_by_id(db: Session, city_id: int) -> Optional[City]:
    return db.scalar(select(City).where(City.id == city_id))


def get_cities(db: Session, skip: int = 0, limit: int = 20,
               level: Optional[str] = None, province: Optional[str] = None) -> list[City]:
    """查询城市列表，支持按等级和省份筛选"""
    stmt = select(City)
    if level:
        stmt = stmt.where(City.level == level)
    if province:
        stmt = stmt.where(City.province == province)
    stmt = stmt.offset(skip).limit(limit).order_by(City.id)
    return list(db.scalars(stmt).all())


def create_city(db: Session, **kwargs) -> City:
    city = City(**kwargs)
    db.add(city)
    db.commit()
    db.refresh(city)
    return city


def update_city(db: Session, city: City, **kwargs) -> City:
    for key, value in kwargs.items():
        if value is not None and hasattr(city, key):
            setattr(city, key, value)
    db.commit()
    db.refresh(city)
    return city


def delete_city(db: Session, city: City) -> None:
    db.delete(city)
    db.commit()


# ==================== ScenicSpot ====================

def get_scenic_by_id(db: Session, scenic_id: int) -> Optional[ScenicSpot]:
    return db.scalar(select(ScenicSpot).where(ScenicSpot.id == scenic_id))


def get_scenics_by_city(db: Session, city_id: int, skip: int = 0, limit: int = 20) -> list[ScenicSpot]:
    stmt = select(ScenicSpot).where(ScenicSpot.city_id == city_id)
    stmt = stmt.offset(skip).limit(limit).order_by(ScenicSpot.score.desc())
    return list(db.scalars(stmt).all())


def get_scenics(db: Session, skip: int = 0, limit: int = 20,
                category: Optional[str] = None) -> list[ScenicSpot]:
    """查询景点列表，支持按类别筛选"""
    stmt = select(ScenicSpot)
    if category:
        stmt = stmt.where(ScenicSpot.category == category)
    stmt = stmt.offset(skip).limit(limit).order_by(ScenicSpot.id)
    return list(db.scalars(stmt).all())


def create_scenic(db: Session, **kwargs) -> ScenicSpot:
    scenic = ScenicSpot(**kwargs)
    db.add(scenic)
    db.commit()
    db.refresh(scenic)
    return scenic


def update_scenic(db: Session, scenic: ScenicSpot, **kwargs) -> ScenicSpot:
    for key, value in kwargs.items():
        if value is not None and hasattr(scenic, key):
            setattr(scenic, key, value)
    db.commit()
    db.refresh(scenic)
    return scenic


def delete_scenic(db: Session, scenic: ScenicSpot) -> None:
    db.delete(scenic)
    db.commit()


# ==================== Hotel ====================

def get_hotel_by_id(db: Session, hotel_id: int) -> Optional[Hotel]:
    return db.scalar(select(Hotel).where(Hotel.id == hotel_id))


def get_hotels_by_city(db: Session, city_id: int, skip: int = 0, limit: int = 20) -> list[Hotel]:
    stmt = select(Hotel).where(Hotel.city_id == city_id)
    stmt = stmt.offset(skip).limit(limit).order_by(Hotel.score.desc())
    return list(db.scalars(stmt).all())


def create_hotel(db: Session, **kwargs) -> Hotel:
    hotel = Hotel(**kwargs)
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def update_hotel(db: Session, hotel: Hotel, **kwargs) -> Hotel:
    for key, value in kwargs.items():
        if value is not None and hasattr(hotel, key):
            setattr(hotel, key, value)
    db.commit()
    db.refresh(hotel)
    return hotel


def delete_hotel(db: Session, hotel: Hotel) -> None:
    db.delete(hotel)
    db.commit()


# ==================== Restaurant ====================

def get_restaurant_by_id(db: Session, restaurant_id: int) -> Optional[Restaurant]:
    return db.scalar(select(Restaurant).where(Restaurant.id == restaurant_id))


def get_restaurants_by_city(db: Session, city_id: int, skip: int = 0, limit: int = 20) -> list[Restaurant]:
    stmt = select(Restaurant).where(Restaurant.city_id == city_id)
    stmt = stmt.offset(skip).limit(limit).order_by(Restaurant.score.desc())
    return list(db.scalars(stmt).all())


def create_restaurant(db: Session, **kwargs) -> Restaurant:
    restaurant = Restaurant(**kwargs)
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


def update_restaurant(db: Session, restaurant: Restaurant, **kwargs) -> Restaurant:
    for key, value in kwargs.items():
        if value is not None and hasattr(restaurant, key):
            setattr(restaurant, key, value)
    db.commit()
    db.refresh(restaurant)
    return restaurant


def delete_restaurant(db: Session, restaurant: Restaurant) -> None:
    db.delete(restaurant)
    db.commit()


# ==================== TravelPlan ====================

def get_plan_by_id(db: Session, plan_id: int) -> Optional[TravelPlan]:
    return db.scalar(select(TravelPlan).where(TravelPlan.id == plan_id))


def get_plans_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 20) -> list[TravelPlan]:
    stmt = select(TravelPlan).where(TravelPlan.user_id == user_id)
    stmt = stmt.offset(skip).limit(limit).order_by(TravelPlan.created_at.desc())
    return list(db.scalars(stmt).all())


def create_plan(db: Session, user_id: int, **kwargs) -> TravelPlan:
    plan = TravelPlan(user_id=user_id, **kwargs)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db: Session, plan: TravelPlan, **kwargs) -> TravelPlan:
    for key, value in kwargs.items():
        if value is not None and hasattr(plan, key):
            setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, plan: TravelPlan) -> None:
    db.delete(plan)
    db.commit()
