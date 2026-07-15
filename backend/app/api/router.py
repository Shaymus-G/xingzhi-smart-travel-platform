from fastapi import APIRouter

from app.api import health, user, travel, recommendation, ai

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
