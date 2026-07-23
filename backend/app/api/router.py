from fastapi import APIRouter

from app.api import health, user, travel, recommendation, ai, weather, recommend, transit

router = APIRouter()

# 健康检查
router.include_router(health.router, prefix="/api")

# 用户 & 偏好
router.include_router(user.router, prefix="/api")

# 旅游资源（城市/景点/酒店/餐厅/旅行计划）
router.include_router(travel.router, prefix="/api")

# 收藏 & 评论
router.include_router(recommendation.router, prefix="/api")

# AI 聊天
router.include_router(ai.router, prefix="/api")

# 天气（OpenWeatherMap）
router.include_router(weather.router, prefix="/api")

# 个性化推荐
router.include_router(recommend.router, prefix="/api")

# 交通路径规划（高德地图）
router.include_router(transit.router, prefix="/api")
