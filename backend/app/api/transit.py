"""交通路径规划 API（高德地图）"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import transit_service
from app.utils.response import success, error

router = APIRouter(prefix="/transit", tags=["交通路径"])


@router.get("/route", summary="两点间路径规划")
async def get_route(
    from_type: str = Query(..., description="起点类型: scenic_spot/hotel/restaurant/entertainment/shopping_mall"),
    from_id: int = Query(..., ge=1, description="起点资源 ID"),
    to_type: str = Query(..., description="终点类型"),
    to_id: int = Query(..., ge=1, description="终点资源 ID"),
    method: str = Query("transit", description="出行方式: transit/driving/walking/bicycling"),
    city: str = Query(None, description="城市名（公交模式必填）"),
    db: Session = Depends(get_db),
):
    """
    两点间路径规划，支持四种出行方式：
    - transit（公交）：含公交/地铁线路号、换乘站、步行距离、票价
    - driving（驾车）：路线距离、预计时长、红绿灯数、高速费
    - walking（步行）：路线指引、距离、时间
    - bicycling（骑行）：骑行路线、距离、时间
    """
    result = await transit_service.get_route(
        db, from_type, from_id, to_type, to_id, method, city,
    )
    if "error" in result:
        return error(code=1, message=result["error"])
    return success(data=result)


@router.get("/between-spots", summary="景点间路径规划")
async def get_route_between_spots(
    spot_a_id: int = Query(..., ge=1, description="景点 A 的 ID"),
    spot_b_id: int = Query(..., ge=1, description="景点 B 的 ID"),
    method: str = Query("transit", description="出行方式: transit/driving/walking/bicycling"),
    db: Session = Depends(get_db),
):
    """
    快捷接口：景点 A → 景点 B 路径规划，自动获取城市名。
    适用于 AI 旅行计划中相邻景点的交通衔接。
    """
    result = await transit_service.get_route_between_spots(
        db, spot_a_id, spot_b_id, method,
    )
    if "error" in result:
        return error(code=1, message=result["error"])
    return success(data=result)
