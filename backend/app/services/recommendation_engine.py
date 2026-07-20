"""个性化推荐引擎：周边 / 相似 / 反差城市 + 协同过滤"""
import math
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.city import City
from app.models.scenic import ScenicSpot
from app.models.favorite import Favorite
from app.models.preference import UserPreference

_REGIONS = {
    "华北": ["北京", "天津", "河北", "山西", "内蒙古"],
    "东北": ["辽宁", "吉林", "黑龙江"],
    "华东": ["上海", "江苏", "浙江", "安徽", "福建", "江西", "山东"],
    "华中": ["河南", "湖北", "湖南"],
    "华南": ["广东", "广西", "海南"],
    "西南": ["重庆", "四川", "贵州", "云南", "西藏"],
    "西北": ["陕西", "甘肃", "青海", "宁夏", "新疆"],
    "港澳台": ["香港", "澳门", "台湾"],
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_region(province: str) -> str:
    if not province:
        return "其他"
    for region, provs in _REGIONS.items():
        for p in provs:
            if province.startswith(p):
                return region
    return "其他"


def _load_category_map(db: Session) -> dict:
    """一次性加载所有城市的景点类别集合，避免 N+1 查询"""
    rows = db.execute(
        select(ScenicSpot.city_id, ScenicSpot.category)
        .where(ScenicSpot.category.isnot(None))
        .distinct()
    ).all()
    mapping: dict[int, set] = {}
    for city_id, cat in rows:
        mapping.setdefault(city_id, set()).add(cat)
    return mapping


def get_nearby_cities(db: Session, city_id: int, radius_km: float = 200, limit: int = 8) -> list[dict]:
    """推荐周边城市（Haversine 距离排序）"""
    city = db.get(City, city_id)
    if not city or not city.latitude or not city.longitude:
        return []

    cities = db.scalars(
        select(City).where(
            City.id != city_id,
            City.latitude.isnot(None),
            City.longitude.isnot(None),
        )
    ).all()

    results = []
    for c in cities:
        dist = _haversine(float(city.latitude), float(city.longitude),
                          float(c.latitude), float(c.longitude))
        if dist <= radius_km:
            results.append({
                "city_id": c.id, "city_name": c.name, "province": c.province,
                "distance_km": round(dist, 1), "level": c.level, "cover_image": c.cover_image,
            })

    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]


def get_similar_cities(db: Session, city_id: int, limit: int = 8) -> list[dict]:
    """推荐相似城市（同区域 + 同等级 + 景点类别 Jaccard）"""
    city = db.get(City, city_id)
    if not city:
        return []

    city_region = _get_region(city.province or "")
    city_level = city.level
    cat_map = _load_category_map(db)
    city_categories = cat_map.get(city_id, set())

    cities = db.scalars(select(City).where(City.id != city_id)).all()

    results = []
    for c in cities:
        c_categories = cat_map.get(c.id, set())
        score = 0.0
        if _get_region(c.province or "") == city_region:
            score += 3.0
        if c.level == city_level:
            score += 1.5
        if city_categories and c_categories:
            overlap = len(city_categories & c_categories)
            total = len(city_categories | c_categories)
            score += (overlap / total) * 4.0 if total > 0 else 0

        results.append({
            "city_id": c.id, "city_name": c.name, "province": c.province,
            "level": c.level, "score": round(score, 1),
            "reason": _similar_reason(_get_region(c.province or "") == city_region,
                                      c.level == city_level,
                                      len(city_categories & c_categories)),
            "cover_image": c.cover_image,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def _similar_reason(same_region: bool, same_level: bool, overlap: int) -> str:
    parts = []
    if same_region:
        parts.append("同区域")
    if same_level:
        parts.append("同热度等级")
    if overlap > 0:
        parts.append(f"景点类型相似({overlap}类重合)")
    return "、".join(parts) if parts else "综合相似"


def get_contrast_cities(db: Session, city_id: int, limit: int = 8) -> list[dict]:
    """推荐反差城市"""
    city = db.get(City, city_id)
    if not city:
        return []

    city_region = _get_region(city.province or "")
    city_level = city.level
    cat_map = _load_category_map(db)
    city_categories = cat_map.get(city_id, set())
    level_order = {"小众": 0, "普通": 1, "热门": 2}

    cities = db.scalars(select(City).where(City.id != city_id)).all()

    results = []
    for c in cities:
        c_categories = cat_map.get(c.id, set())
        contrast = 0.0
        if _get_region(c.province or "") != city_region:
            contrast += 3.0
        level_diff = abs(level_order.get(c.level, 1) - level_order.get(city_level, 1))
        contrast += level_diff * 1.5
        if city_categories and c_categories:
            overlap = len(city_categories & c_categories)
            total = len(city_categories | c_categories)
            jaccard = overlap / total if total > 0 else 0
            contrast += (1 - jaccard) * 4.0

        results.append({
            "city_id": c.id, "city_name": c.name, "province": c.province,
            "level": c.level, "score": round(contrast, 1),
            "reason": _contrast_reason(_get_region(c.province or "") != city_region,
                                       c.level, city_level,
                                       len(c_categories - city_categories)),
            "cover_image": c.cover_image,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def _contrast_reason(diff_region: bool, c_level: str, my_level: str, diff_count: int) -> str:
    parts = []
    if diff_region:
        parts.append("不同区域")
    if c_level != my_level:
        parts.append(f"{my_level}→{c_level}")
    if diff_count > 0:
        parts.append(f"新鲜类型({diff_count}类)")
    return "、".join(parts) if parts else "换个口味"


def get_collaborative_recommendations(db: Session, user_id: int, limit: int = 8) -> list[dict]:
    """协同过滤：找到相似用户收藏的城市"""
    # 获取当前用户偏好向量
    my_prefs = {}
    for row in db.execute(
        select(UserPreference.preference_value, UserPreference.weight)
        .where(UserPreference.user_id == user_id)
    ).all():
        my_prefs[row[0]] = row[1]

    # 获取当前用户已收藏景点的城市 ID
    my_fav_rows = db.execute(
        select(ScenicSpot.city_id).join(
            Favorite, Favorite.target_id == ScenicSpot.id
        ).where(
            Favorite.user_id == user_id,
            Favorite.target_type == "scenic_spot",
        ).distinct()
    ).all()
    my_fav_city_ids = {row[0] for row in my_fav_rows}

    # 获取其他用户
    other_users = db.execute(
        select(Favorite.user_id).where(Favorite.user_id != user_id).distinct()
    ).all()

    results = []
    for (other_id,) in other_users:
        # 获取该用户偏好
        other_prefs = {}
        for row in db.execute(
            select(UserPreference.preference_value, UserPreference.weight)
            .where(UserPreference.user_id == other_id)
        ).all():
            other_prefs[row[0]] = row[1]

        sim = _cosine_similarity(my_prefs, other_prefs)

        # 获取该用户收藏的城市
        other_cities = db.execute(
            select(ScenicSpot.city_id, City.name, City.province, City.level, City.cover_image)
            .join(City, ScenicSpot.city_id == City.id)
            .join(Favorite, Favorite.target_id == ScenicSpot.id)
            .where(
                Favorite.user_id == other_id,
                Favorite.target_type == "scenic_spot",
            ).distinct()
        ).all()

        for cid, cname, cprov, clevel, cimage in other_cities:
            if cid not in my_fav_city_ids:
                results.append({
                    "city_id": cid, "city_name": cname, "province": cprov,
                    "level": clevel, "score": round(sim, 3),
                    "reason": "相似用户也收藏了", "cover_image": cimage,
                })

    # 去重排序
    seen = set()
    unique = []
    for item in sorted(results, key=lambda x: x["score"], reverse=True):
        if item["city_id"] not in seen:
            seen.add(item["city_id"])
            unique.append(item)

    return unique[:limit]


def _cosine_similarity(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    all_keys = set(a.keys()) | set(b.keys())
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in all_keys)
    norm_a = math.sqrt(sum(v ** 2 for v in a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
