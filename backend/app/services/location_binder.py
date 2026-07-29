"""AI 旅行计划地点绑定服务 — 同名消歧 + 坐标回填"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.scenic import ScenicSpot
from app.models.hotel import Hotel
from app.models.restaurant import Restaurant
from app.models.entertainment import Entertainment
from app.models.shopping_mall import ShoppingMall

_RESOURCE_MODELS = {
    "scenic_spot": ScenicSpot,
    "hotel": Hotel,
    "restaurant": Restaurant,
    "entertainment": Entertainment,
    "shopping_mall": ShoppingMall,
}


def bind_plan_locations(plan_json: dict, destination_city_id: int, db: Session) -> dict:
    """遍历 AI 生成的 plan_json，为每个节点绑定真实资源坐标。

    Returns:
        修改后的 plan_json（原地修改并返回）
    """
    if not isinstance(plan_json, dict):
        return plan_json

    itinerary = plan_json.get("itinerary", [])
    if not isinstance(itinerary, list):
        return plan_json

    for day in itinerary:
        for item in day.get("items", []):
            _bind_item(item, destination_city_id, db)
        for meal in day.get("meals", []):
            _bind_item(meal, destination_city_id, db)
        hotel = day.get("hotel")
        if hotel:
            _bind_item(hotel, destination_city_id, db)

    return plan_json


def _bind_item(item: dict, city_id: int, db: Session):
    """绑定单个行程节点到真实资源"""
    if not isinstance(item, dict):
        return

    res_type = item.get("resource_type", "")
    res_id = item.get("resource_id")
    name = item.get("name", "")

    # 尝试通过 resource_id 精确查找
    resource = _find_by_id(db, res_type, res_id, city_id)
    if resource:
        _apply_binding(item, resource, "matched", "resource_database")
        return

    # 通过名称在同城市内模糊匹配
    resource = _find_by_name(db, res_type, name, city_id)
    if resource:
        _apply_binding(item, resource, "matched", "resource_database")
        return

    # 无法匹配
    _apply_failed_binding(item)


def _find_by_id(db: Session, res_type: str, res_id, city_id: int):
    """通过 resource_id 查找，并校验城市"""
    if not res_id or res_type not in _RESOURCE_MODELS:
        return None
    model = _RESOURCE_MODELS[res_type]
    resource = db.scalar(select(model).where(model.id == int(res_id)))
    if resource and getattr(resource, "city_id", None) == city_id:
        return resource
    return None


def _find_by_name(db: Session, res_type: str, name: str, city_id: int):
    """在同城市同类型资源中按名称精确匹配"""
    if not name or res_type not in _RESOURCE_MODELS:
        return None
    model = _RESOURCE_MODELS[res_type]
    candidates = db.scalars(
        select(model).where(model.city_id == city_id, model.name == name)
    ).all()
    if len(candidates) == 1:
        return candidates[0]
    return None  # 多个同名或找不到


def _apply_binding(item: dict, resource, status: str, source: str):
    """回填真实坐标和地址"""
    item["resource_id"] = resource.id
    item["resource_type"] = _get_resource_type(resource)
    item["name"] = resource.name
    item["address"] = getattr(resource, "address", None)
    item["city_id"] = getattr(resource, "city_id", None)
    item["latitude"] = float(resource.latitude) if getattr(resource, "latitude", None) else None
    item["longitude"] = float(resource.longitude) if getattr(resource, "longitude", None) else None
    item["coordinate_system"] = "GCJ-02"
    item["location_match_status"] = status
    item["location_match_source"] = source


def _apply_failed_binding(item: dict):
    """匹配失败时的字段清理"""
    item["resource_id"] = None
    item["city_id"] = None
    item["latitude"] = None
    item["longitude"] = None
    item["coordinate_system"] = None
    item["location_match_status"] = "not_found"
    item["location_match_source"] = "none"


def _get_resource_type(resource) -> str:
    for rt, model in _RESOURCE_MODELS.items():
        if isinstance(resource, model):
            return rt
    return ""
