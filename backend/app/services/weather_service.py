"""OpenWeatherMap 天气 API 服务"""
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.config import settings
from app.models.city import City

OWM_BASE = "https://api.openweathermap.org/data/2.5"


def _find_city(db: Session, city_name: str) -> Optional[tuple]:
    """从数据库查询城市坐标。

    优先精确匹配，失败则模糊匹配（支持"北京"匹配"北京东城区"）。
    返回 (实际城市名, lat, lon) 或 None。
    """
    # 精确匹配
    stmt = select(City).where(City.name == city_name)
    city = db.scalar(stmt)
    if city and city.latitude and city.longitude:
        return (city.name, float(city.latitude), float(city.longitude))

    # 模糊匹配
    stmt = select(City).where(City.name.like(f"{city_name}%"))
    cities = db.scalars(stmt).all()
    for city in cities:
        if city.latitude and city.longitude:
            return (city.name, float(city.latitude), float(city.longitude))

    return None


def _parse_weather(data: dict, real_name: str, query: str) -> dict:
    """解析 OpenWeatherMap 当前天气响应"""
    return {
        "city": real_name,
        "query": query,
        "temperature": f"{data['main']['temp']:.0f}°C",
        "feels_like": f"{data['main']['feels_like']:.0f}°C",
        "weather": data["weather"][0]["description"],
        "weather_icon": data["weather"][0]["icon"],
        "humidity": f"{data['main']['humidity']}%",
        "pressure": f"{data['main']['pressure']} hPa",
        "wind_speed": f"{data['wind'].get('speed', 0):.1f} m/s",
        "visibility": f"{data.get('visibility', 'N/A')}m",
        "clouds": f"{data['clouds']['all']}%",
    }


async def get_current_weather(db: Session, city_name: str) -> dict:
    """获取城市实时天气"""
    result = _find_city(db, city_name)
    if not result:
        return {"error": f"未找到城市「{city_name}」，请检查城市名"}

    real_name, lat, lon = result

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{OWM_BASE}/weather",
            params={
                "lat": lat,
                "lon": lon,
                "appid": settings.OPENWEATHER_KEY,
                "lang": "zh_cn",
                "units": "metric",
            },
        )
        data = resp.json()

    if data.get("cod") != 200:
        return {"error": f"天气查询失败: {data.get('message', '未知错误')}"}

    return _parse_weather(data, real_name, city_name)


async def get_forecast(db: Session, city_name: str, days: int = 7) -> dict:
    """获取未来天气预报。

    OpenWeatherMap 免费版返回 5 天/3 小时间隔的数据。
    这里按天聚合，取每天的最高/最低温度和主要天气。
    """
    result = _find_city(db, city_name)
    if not result:
        return {"error": f"未找到城市「{city_name}」，请检查城市名"}

    real_name, lat, lon = result

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{OWM_BASE}/forecast",
            params={
                "lat": lat,
                "lon": lon,
                "appid": settings.OPENWEATHER_KEY,
                "lang": "zh_cn",
                "units": "metric",
            },
        )
        data = resp.json()

    if data.get("cod") != "200":
        return {"error": f"预报查询失败: {data.get('message', '未知错误')}"}

    # 按天聚合（免费版 5 天/3 小时，共 40 条）
    from collections import defaultdict
    daily = defaultdict(lambda: {"temps": [], "weathers": [], "icons": []})

    for item in data["list"]:
        date = item["dt_txt"][:10]  # "2026-07-16"
        daily[date]["temps"].append(item["main"]["temp"])
        daily[date]["weathers"].append(item["weather"][0]["description"])
        daily[date]["icons"].append(item["weather"][0]["icon"])

    forecast_list = []
    for date, vals in sorted(daily.items())[:days]:
        # 取最常出现的天气描述
        weather_desc = max(set(vals["weathers"]), key=vals["weathers"].count)
        forecast_list.append({
            "date": date,
            "temp_high": f"{max(vals['temps']):.0f}°C",
            "temp_low": f"{min(vals['temps']):.0f}°C",
            "weather": weather_desc,
            "weather_icon": vals["icons"][0],
        })

    return {
        "city": real_name,
        "query": city_name,
        "days": len(forecast_list),
        "forecast": forecast_list,
    }
