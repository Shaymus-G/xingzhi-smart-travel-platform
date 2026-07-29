"""旅游资源 API：城市 / 景点 / 酒店 / 餐厅 / 娱乐 / 商场 / 旅行计划"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.city import CityCreate, CityUpdate, CityResponse
from app.schemas.scenic import ScenicSpotCreate, ScenicSpotUpdate, ScenicSpotResponse
from app.schemas.hotel import HotelCreate, HotelUpdate, HotelResponse
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate, RestaurantResponse
from app.schemas.entertainment import EntertainmentCreate, EntertainmentUpdate, EntertainmentResponse
from app.schemas.shopping_mall import ShoppingMallCreate, ShoppingMallUpdate, ShoppingMallResponse
from app.schemas.travel import TravelPlanCreate, TravelPlanUpdate, TravelPlanResponse
from app.services import travel_service, share_service
from app.utils.response import success

router = APIRouter(prefix="/travel", tags=["旅游资源"])


# ==================== City ====================

@router.get("/cities", response_model=dict)
def list_cities(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    level: Optional[str] = None,
    province: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """城市列表，支持按等级(热门/普通/小众)和省份筛选"""
    cities = travel_service.get_cities(db, skip=skip, limit=limit, level=level, province=province)
    return success(data=[CityResponse.model_validate(c).model_dump() for c in cities])


@router.get("/cities/{city_id}", response_model=dict)
def get_city(city_id: int, db: Session = Depends(get_db)):
    """城市详情"""
    city = travel_service.get_city_by_id(db, city_id)
    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    return success(data=CityResponse.model_validate(city).model_dump())


@router.post("/cities", response_model=dict)
def create_city(data: CityCreate, db: Session = Depends(get_db)):
    """新增城市"""
    city = travel_service.create_city(db, **data.model_dump())
    return success(data=CityResponse.model_validate(city).model_dump(), message="城市创建成功")


@router.put("/cities/{city_id}", response_model=dict)
def update_city(city_id: int, data: CityUpdate, db: Session = Depends(get_db)):
    """更新城市"""
    city = travel_service.get_city_by_id(db, city_id)
    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    city = travel_service.update_city(db, city, **data.model_dump(exclude_unset=True))
    return success(data=CityResponse.model_validate(city).model_dump(), message="城市更新成功")


@router.delete("/cities/{city_id}", response_model=dict)
def delete_city(city_id: int, db: Session = Depends(get_db)):
    """删除城市"""
    city = travel_service.get_city_by_id(db, city_id)
    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    travel_service.delete_city(db, city)
    return success(message="城市已删除")


# ==================== ScenicSpot ====================

@router.get("/scenics", response_model=dict)
def list_scenics(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    city_id: Optional[int] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """景点列表，支持按城市和类别筛选"""
    if city_id:
        scenics = travel_service.get_scenics_by_city(db, city_id, skip=skip, limit=limit)
    else:
        scenics = travel_service.get_scenics(db, skip=skip, limit=limit, category=category)
    return success(data=[ScenicSpotResponse.model_validate(s).model_dump() for s in scenics])


@router.get("/scenics/{scenic_id}", response_model=dict)
def get_scenic(scenic_id: int, db: Session = Depends(get_db)):
    """景点详情"""
    scenic = travel_service.get_scenic_by_id(db, scenic_id)
    if scenic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="景点不存在")
    return success(data=ScenicSpotResponse.model_validate(scenic).model_dump())


@router.post("/scenics", response_model=dict)
def create_scenic(data: ScenicSpotCreate, db: Session = Depends(get_db)):
    """新增景点"""
    scenic = travel_service.create_scenic(db, **data.model_dump())
    return success(data=ScenicSpotResponse.model_validate(scenic).model_dump(), message="景点创建成功")


@router.put("/scenics/{scenic_id}", response_model=dict)
def update_scenic(scenic_id: int, data: ScenicSpotUpdate, db: Session = Depends(get_db)):
    """更新景点"""
    scenic = travel_service.get_scenic_by_id(db, scenic_id)
    if scenic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="景点不存在")
    scenic = travel_service.update_scenic(db, scenic, **data.model_dump(exclude_unset=True))
    return success(data=ScenicSpotResponse.model_validate(scenic).model_dump(), message="景点更新成功")


@router.delete("/scenics/{scenic_id}", response_model=dict)
def delete_scenic(scenic_id: int, db: Session = Depends(get_db)):
    """删除景点"""
    scenic = travel_service.get_scenic_by_id(db, scenic_id)
    if scenic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="景点不存在")
    travel_service.delete_scenic(db, scenic)
    return success(message="景点已删除")


# ==================== Hotel ====================

@router.get("/hotels", response_model=dict)
def list_hotels(
    city_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """酒店列表，支持按城市筛选"""
    if city_id:
        hotels = travel_service.get_hotels_by_city(db, city_id, skip=skip, limit=limit)
    else:
        # 没有 city_id 时返回空列表或全部（这里返回空，前端应传入 city_id）
        hotels = []
    return success(data=[HotelResponse.model_validate(h).model_dump() for h in hotels])


@router.get("/hotels/{hotel_id}", response_model=dict)
def get_hotel(hotel_id: int, db: Session = Depends(get_db)):
    """酒店详情"""
    hotel = travel_service.get_hotel_by_id(db, hotel_id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="酒店不存在")
    return success(data=HotelResponse.model_validate(hotel).model_dump())


@router.post("/hotels", response_model=dict)
def create_hotel(data: HotelCreate, db: Session = Depends(get_db)):
    """新增酒店"""
    hotel = travel_service.create_hotel(db, **data.model_dump())
    return success(data=HotelResponse.model_validate(hotel).model_dump(), message="酒店创建成功")


@router.put("/hotels/{hotel_id}", response_model=dict)
def update_hotel(hotel_id: int, data: HotelUpdate, db: Session = Depends(get_db)):
    """更新酒店"""
    hotel = travel_service.get_hotel_by_id(db, hotel_id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="酒店不存在")
    hotel = travel_service.update_hotel(db, hotel, **data.model_dump(exclude_unset=True))
    return success(data=HotelResponse.model_validate(hotel).model_dump(), message="酒店更新成功")


@router.delete("/hotels/{hotel_id}", response_model=dict)
def delete_hotel(hotel_id: int, db: Session = Depends(get_db)):
    """删除酒店"""
    hotel = travel_service.get_hotel_by_id(db, hotel_id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="酒店不存在")
    travel_service.delete_hotel(db, hotel)
    return success(message="酒店已删除")


# ==================== Restaurant ====================

@router.get("/restaurants", response_model=dict)
def list_restaurants(
    city_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """餐厅列表，支持按城市筛选"""
    if city_id:
        restaurants = travel_service.get_restaurants_by_city(db, city_id, skip=skip, limit=limit)
    else:
        restaurants = []
    return success(data=[RestaurantResponse.model_validate(r).model_dump() for r in restaurants])


@router.get("/restaurants/{restaurant_id}", response_model=dict)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """餐厅详情"""
    restaurant = travel_service.get_restaurant_by_id(db, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="餐厅不存在")
    return success(data=RestaurantResponse.model_validate(restaurant).model_dump())


@router.post("/restaurants", response_model=dict)
def create_restaurant(data: RestaurantCreate, db: Session = Depends(get_db)):
    """新增餐厅"""
    restaurant = travel_service.create_restaurant(db, **data.model_dump())
    return success(data=RestaurantResponse.model_validate(restaurant).model_dump(), message="餐厅创建成功")


@router.put("/restaurants/{restaurant_id}", response_model=dict)
def update_restaurant(restaurant_id: int, data: RestaurantUpdate, db: Session = Depends(get_db)):
    """更新餐厅"""
    restaurant = travel_service.get_restaurant_by_id(db, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="餐厅不存在")
    restaurant = travel_service.update_restaurant(db, restaurant, **data.model_dump(exclude_unset=True))
    return success(data=RestaurantResponse.model_validate(restaurant).model_dump(), message="餐厅更新成功")


@router.delete("/restaurants/{restaurant_id}", response_model=dict)
def delete_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """删除餐厅"""
    restaurant = travel_service.get_restaurant_by_id(db, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="餐厅不存在")
    travel_service.delete_restaurant(db, restaurant)
    return success(message="餐厅已删除")


# ==================== Entertainment ====================

@router.get("/entertainments", response_model=dict)
def list_entertainments(
    city_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """娱乐场所列表，支持按城市筛选"""
    if city_id:
        entertainments = travel_service.get_entertainments_by_city(db, city_id, skip=skip, limit=limit)
    else:
        entertainments = []
    return success(data=[EntertainmentResponse.model_validate(e).model_dump() for e in entertainments])


@router.get("/entertainments/{eid}", response_model=dict)
def get_entertainment(eid: int, db: Session = Depends(get_db)):
    """娱乐场所详情"""
    e = travel_service.get_entertainment_by_id(db, eid)
    if e is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="娱乐场所不存在")
    return success(data=EntertainmentResponse.model_validate(e).model_dump())


@router.post("/entertainments", response_model=dict)
def create_entertainment(data: EntertainmentCreate, db: Session = Depends(get_db)):
    """新增娱乐场所"""
    e = travel_service.create_entertainment(db, **data.model_dump())
    return success(data=EntertainmentResponse.model_validate(e).model_dump(), message="创建成功")


# ==================== ShoppingMall ====================

@router.get("/malls", response_model=dict)
def list_malls(
    city_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """商场列表，支持按城市筛选"""
    if city_id:
        malls = travel_service.get_malls_by_city(db, city_id, skip=skip, limit=limit)
    else:
        malls = []
    return success(data=[ShoppingMallResponse.model_validate(m).model_dump() for m in malls])


@router.get("/malls/{mid}", response_model=dict)
def get_mall(mid: int, db: Session = Depends(get_db)):
    """商场详情"""
    m = travel_service.get_mall_by_id(db, mid)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商场不存在")
    return success(data=ShoppingMallResponse.model_validate(m).model_dump())


@router.post("/malls", response_model=dict)
def create_mall(data: ShoppingMallCreate, db: Session = Depends(get_db)):
    """新增商场"""
    m = travel_service.create_mall(db, **data.model_dump())
    return success(data=ShoppingMallResponse.model_validate(m).model_dump(), message="创建成功")


# ==================== TravelPlan ====================

@router.get("/plans", response_model=dict)
def list_my_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的旅行计划列表"""
    plans = travel_service.get_plans_by_user(db, current_user.id, skip=skip, limit=limit)
    return success(data=[TravelPlanResponse.model_validate(p).model_dump() for p in plans])


@router.get("/plans/{plan_id}", response_model=dict)
def get_plan(plan_id: int, current_user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """旅行计划详情"""
    plan = travel_service.get_plan_by_id(db, plan_id)
    if plan is None or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计划不存在")
    return success(data=TravelPlanResponse.model_validate(plan).model_dump())


@router.post("/plans", response_model=dict)
def create_plan(data: TravelPlanCreate, current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """创建旅行计划"""
    plan = travel_service.create_plan(db, current_user.id, **data.model_dump())
    return success(data=TravelPlanResponse.model_validate(plan).model_dump(), message="计划创建成功")


@router.put("/plans/{plan_id}", response_model=dict)
def update_plan(plan_id: int, data: TravelPlanUpdate,
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """更新旅行计划"""
    plan = travel_service.get_plan_by_id(db, plan_id)
    if plan is None or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计划不存在")
    plan = travel_service.update_plan(db, plan, **data.model_dump(exclude_unset=True))
    return success(data=TravelPlanResponse.model_validate(plan).model_dump(), message="计划更新成功")


@router.delete("/plans/{plan_id}", response_model=dict)
def delete_plan(plan_id: int, current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """删除旅行计划"""
    plan = travel_service.get_plan_by_id(db, plan_id)
    if plan is None or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计划不存在")
    travel_service.delete_plan(db, plan)
    return success(message="计划已删除")


# ==================== Plan Share ====================

share_router = APIRouter(prefix="/public", tags=["公开分享"])


@router.post("/plans/{plan_id}/shares", response_model=dict)
def create_plan_share(
    plan_id: int,
    expires_in_hours: int = Query(72, ge=1, le=720, description="有效期（小时）"),
    include_budget: bool = Query(False, description="是否公开预算"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建旅行计划的公开分享链接"""
    result = share_service.create_share(
        db, plan_id, current_user.id, expires_in_hours, include_budget
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return success(data=result, message="分享创建成功")


@router.get("/plans/{plan_id}/shares", response_model=dict)
def list_plan_shares(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看计划的分享记录"""
    shares = share_service.get_shares_by_plan(db, plan_id, current_user.id)
    return success(data=shares)


@router.delete("/plans/{plan_id}/shares/{share_id}", response_model=dict)
def revoke_plan_share(
    plan_id: int, share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """撤销分享"""
    ok = share_service.revoke_share(db, plan_id, share_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分享不存在")
    return success(message="分享已撤销")


@share_router.get("/plan-shares/{token}", response_model=dict)
def get_public_share(token: str, db: Session = Depends(get_db)):
    """公开访问分享快照（无需登录）"""
    snapshot = share_service.get_public_share(db, token)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分享不存在或已过期")
    return success(data=snapshot)
