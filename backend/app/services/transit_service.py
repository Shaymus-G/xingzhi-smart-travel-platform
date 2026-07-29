"""高德地图路径规划服务 — 公交/驾车/步行/骑行"""
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.city import City
from app.models.scenic import ScenicSpot
from app.services.travel_service import get_scenic_by_id

AMAP_BASE = "https://restapi.amap.com/v3/direction"


async def get_route(
    db: Session,
    from_type: str, from_id: int,
    to_type: str, to_id: int,
    method: str = "transit",
    city: Optional[str] = None,
) -> dict:
    """计算两点间路径规划。

    Args:
        from_type / to_type: scenic_spot / hotel / restaurant / entertainment / shopping_mall
        from_id / to_id: 数据库 ID
        method: transit（公交）/ driving（驾车）/ walking（步行）/ bicycling（骑行）
        city: 城市名（公交模式必填，用于限定搜索范围）

    Returns:
        路径规划结果字典或包含 error 的字典
    """
    # 1. 获取起点坐标
    origin = _get_coords(db, from_type, from_id)
    if not origin:
        return {"error": f"未找到起点资源"}

    # 2. 获取终点坐标
    dest = _get_coords(db, to_type, to_id)
    if not dest:
        return {"error": f"未找到终点资源"}

    origin_str = f"{origin[0]},{origin[1]}"
    dest_str = f"{dest[0]},{dest[1]}"

    # 3. 根据出行方式调用不同 API
    if method == "transit":
        if not city:
            return {"error": "公交模式需要提供 city 参数"}
        return await _call_transit(origin_str, dest_str, city)
    elif method == "driving":
        return await _call_driving(origin_str, dest_str)
    elif method == "walking":
        return await _call_walking(origin_str, dest_str)
    elif method == "bicycling":
        return await _call_bicycling(origin_str, dest_str)
    else:
        return {"error": f"不支持的出行方式: {method}"}


async def get_route_between_spots(
    db: Session,
    spot_a_id: int,
    spot_b_id: int,
    method: str = "transit",
) -> dict:
    """景点 A → 景点 B 路径规划（自动获取 city）"""
    spot_a = get_scenic_by_id(db, spot_a_id)
    spot_b = get_scenic_by_id(db, spot_b_id)
    if not spot_a or not spot_b:
        return {"error": "景点不存在"}

    # 自动获取城市名
    city = db.get(City, spot_a.city_id)
    city_name = city.name if city else None

    return await get_route(
        db, "scenic_spot", spot_a_id,
        "scenic_spot", spot_b_id,
        method, city_name,
    )


def _get_coords(db: Session, res_type: str, res_id: int) -> Optional[tuple]:
    """根据资源类型和 ID 获取经纬度 (lng, lat)"""
    if res_type == "scenic_spot":
        r = get_scenic_by_id(db, res_id)
    elif res_type == "hotel":
        from app.services.travel_service import get_hotel_by_id
        r = get_hotel_by_id(db, res_id)
    elif res_type == "restaurant":
        from app.services.travel_service import get_restaurant_by_id
        r = get_restaurant_by_id(db, res_id)
    elif res_type == "entertainment":
        from app.services.travel_service import get_entertainment_by_id
        r = get_entertainment_by_id(db, res_id)
    elif res_type == "shopping_mall":
        from app.services.travel_service import get_mall_by_id
        r = get_mall_by_id(db, res_id)
    else:
        return None

    if r and r.longitude and r.latitude:
        return (float(r.longitude), float(r.latitude))
    return None


# ==================== 高德 API 调用 ====================

async def _call_transit(origin: str, destination: str, city: str) -> dict:
    """公交路径规划"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{AMAP_BASE}/transit/integrated",
            params={
                "origin": origin, "destination": destination,
                "city": city, "key": settings.AMAP_KEY,
            },
        )
        data = resp.json()

    if data.get("status") != "1":
        return {"error": f"路径规划失败: {data.get('info', '未知错误')}"}

    return _parse_transit(data, origin, destination)


async def _call_driving(origin: str, destination: str) -> dict:
    """驾车路径规划"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{AMAP_BASE}/driving",
            params={
                "origin": origin, "destination": destination,
                "key": settings.AMAP_KEY, "extensions": "base",
            },
        )
        data = resp.json()

    if data.get("status") != "1":
        return {"error": f"路径规划失败: {data.get('info', '未知错误')}"}

    route = data["route"]["paths"][0]
    return {
        "method": "driving",
        "distance": f"{route['distance']} 米",
        "duration": f"{int(route['duration']) // 60} 分钟",
        "traffic_lights": route.get("traffic_lights", 0),
        "toll": f"{route.get('tolls', 0)} 元",
        "steps": [
            {"instruction": s["instruction"], "distance": s["distance"]}
            for s in route["steps"][:5]
        ],
    }


async def _call_walking(origin: str, destination: str) -> dict:
    """步行路径规划"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{AMAP_BASE}/walking",
            params={
                "origin": origin, "destination": destination,
                "key": settings.AMAP_KEY,
            },
        )
        data = resp.json()

    if data.get("status") != "1":
        return {"error": f"路径规划失败: {data.get('info', '未知错误')}"}

    route = data["route"]["paths"][0]
    return {
        "method": "walking",
        "distance": f"{route['distance']} 米",
        "duration": f"{int(route['duration']) // 60} 分钟",
        "steps": [
            {"instruction": s["instruction"], "distance": s["distance"]}
            for s in route["steps"][:5]
        ],
    }


async def _call_bicycling(origin: str, destination: str) -> dict:
    """骑行路径规划"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{AMAP_BASE}/bicycling",
            params={
                "origin": origin, "destination": destination,
                "key": settings.AMAP_KEY,
            },
        )
        data = resp.json()

    if data.get("status") != "1":
        return {"error": f"路径规划失败: {data.get('info', '未知错误')}"}

    route = data["route"]["paths"][0]
    return {
        "method": "bicycling",
        "distance": f"{route['distance']} 米",
        "duration": f"{int(route['duration']) // 60} 分钟",
        "steps": [
            {"instruction": s["instruction"], "distance": s["distance"]}
            for s in route["steps"][:5]
        ],
    }


# ==================== 公交响应解析 ====================

def _parse_transit(data: dict, origin: str, destination: str) -> dict:
    """解析公交路径规划响应"""
    route = data["route"]
    transits = route.get("transits", [])

    if not transits:
        return {
            "method": "transit",
            "distance": f"{route['distance']} 米",
            "duration": "无法计算",
            "steps": [],
            "note": "该路线暂无公交方案，建议选择其他出行方式",
        }

    best = transits[0]  # 推荐方案
    segments = []
    for seg in best.get("segments", []):
        # 步行段
        walking = seg.get("walking")
        if walking:
            segments.append({
                "type": "walking",
                "instruction": walking.get("instruction", "步行"),
                "distance": f"{walking.get('distance', '')} 米",
                "duration": walking.get("duration", ""),
            })

        # 公交段
        bus_lines = seg.get("bus", {}).get("buslines", [])
        for bus in bus_lines:
            segments.append({
                "type": bus.get("type", "bus"),
                "name": bus.get("name", ""),
                "departure": bus.get("departure_stop", {}).get("name", ""),
                "arrival": bus.get("arrival_stop", {}).get("name", ""),
                "via_stops": bus.get("via_stops", 0),
                "distance": bus.get("distance", ""),
                "duration": bus.get("duration", ""),
            })

    return {
        "method": "transit",
        "distance": f"{best['distance']} 米",
        "duration": f"{int(best['duration']) // 60} 分钟",
        "cost": f"{best.get('cost', 0)} 元",
        "walking_distance": f"{best.get('walking_distance', 0)} 米",
        "segments": segments,
    }
