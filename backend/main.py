"""
"行知" 智慧文旅平台 — FastAPI 应用入口
"""
import sys, os
# 将项目根目录加入 Python 路径，确保可以导入 ai/xingzhi_ai 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai"))
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    # 生产环境关闭调试信息泄露
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# ==================== 安全中间件（按顺序加载） ====================

# 1. 请求体大小限制（防大 payload 攻击）
from app.core.middleware import body_size_limit_middleware  # noqa: E402
app.middleware("http")(body_size_limit_middleware)

# 2. 速率限制（防刷接口）
from app.core.middleware import rate_limit_middleware  # noqa: E402
app.middleware("http")(rate_limit_middleware)

# 3. 安全响应头
from app.core.middleware import security_headers_middleware  # noqa: E402
app.middleware("http")(security_headers_middleware)

# 4. CORS（开发阶段全开，生产环境通过环境变量控制）
_cors_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
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
