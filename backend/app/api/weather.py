"""天气 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.weather import WeatherQuery
from app.services import weather_service
from app.utils.response import success, error

router = APIRouter(prefix="/weather", tags=["天气"])


@router.get("/current", summary="获取城市实时天气")
async def get_current_weather(
    city: str = Query(..., description="城市名称，如：杭州"),
    db: Session = Depends(get_db),
):
    """返回指定城市的实时天气（温度、风力、湿度、能见度等）"""
    result = await weather_service.get_current_weather(db, city)
    if "error" in result:
        return error(code=1, message=result["error"])
    return success(data=result)


@router.get("/forecast", summary="获取城市天气预报")
async def get_forecast(
    city: str = Query(..., description="城市名称，如：杭州"),
    days: int = Query(7, ge=3, le=7, description="预报天数（3 或 7）"),
    db: Session = Depends(get_db),
):
    """返回指定城市未来 3 天或 7 天的天气预报"""
    result = await weather_service.get_forecast(db, city, days)
    if "error" in result:
        return error(code=1, message=result["error"])
    return success(data=result)
