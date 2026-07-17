"""
"行知" 智慧文旅平台 — FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

# CORS — 允许前端 H5 开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源，部署时收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "Welcome to XingZhi Backend"
    }


@app.on_event("startup")
def startup():
    """
    应用启动事件。

    注意：数据库表结构已由 Alembic 统一管理，
    不再使用 Base.metadata.create_all()。
    如需创建/更新表结构，请使用：
        alembic revision --autogenerate -m "description"
        alembic upgrade head
    """
    pass
