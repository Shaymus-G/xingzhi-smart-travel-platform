"""个性化推荐 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_optional_user
from app.models.user import User
from app.services import recommendation_engine
from app.utils.response import success, error

router = APIRouter(prefix="/recommend", tags=["个性化推荐"])


@router.get("/nearby", summary="周边城市推荐")
def nearby_cities(
    city_id: int = Query(..., ge=1, description="当前城市 ID"),
    radius_km: float = Query(200, ge=50, le=500, description="搜索半径（km）"),
    limit: int = Query(8, ge=1, le=20, description="返回数量"),
    db: Session = Depends(get_db),
):
    """
    推荐周边城市。

    根据城市经纬度计算 Haversine 距离，推荐半径范围内的城市，按距离升序排列。
    示例：杭州 → 绍兴(60km)、嘉兴(85km)、湖州(75km)
    """
    result = recommendation_engine.get_nearby_cities(db, city_id, radius_km, limit)
    if not result:
        return error(code=1, message="未找到周边城市，请检查城市 ID 是否正确")
    return success(data=result)


@router.get("/similar", summary="相似城市推荐")
def similar_cities(
    city_id: int = Query(..., ge=1, description="当前城市 ID"),
    limit: int = Query(8, ge=1, le=20, description="返回数量"),
    db: Session = Depends(get_db),
):
    """
    推荐相似城市。

    基于多维特征计算相似度：地理区域 + 热度等级 + 景点类别 Jaccard 相似度。
    示例：杭州 → 苏州、扬州（同为华东区域 + 热门 + 江南园林类景点）
    """
    result = recommendation_engine.get_similar_cities(db, city_id, limit)
    if not result:
        return error(code=1, message="未找到相似城市")
    return success(data=result)


@router.get("/contrast", summary="反差城市推荐")
def contrast_cities(
    city_id: int = Query(..., ge=1, description="当前城市 ID"),
    limit: int = Query(8, ge=1, le=20, description="返回数量"),
    db: Session = Depends(get_db),
):
    """
    推荐反差城市。

    推荐与当前城市特征差异最大的城市：不同区域 + 不同等级 + 不同景点类型。
    示例：杭州(华东,热门,园林) → 呼伦贝尔(华北,小众,草原)
    """
    result = recommendation_engine.get_contrast_cities(db, city_id, limit)
    if not result:
        return error(code=1, message="未找到反差城市")
    return success(data=result)


@router.get("/collaborative", summary="协同过滤推荐")
def collaborative(
    current_user: User = Depends(get_optional_user),
    limit: int = Query(8, ge=1, le=20, description="返回数量"),
    db: Session = Depends(get_db),
):
    """
    协同过滤推荐（需要登录）。

    找到与当前用户偏好相似的其他用户，推荐他们收藏过但当前用户未收藏的城市。
    未登录时返回空列表。
    """
    if current_user is None:
        return success(data=[], message="登录后可获得个性化推荐")
    result = recommendation_engine.get_collaborative_recommendations(db, current_user.id, limit)
    return success(data=result)
