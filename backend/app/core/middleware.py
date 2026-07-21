"""安全中间件：速率限制 + 安全头 + 请求体大小限制"""
import time
import asyncio
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# ==================== 安全响应头 ====================

async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    """为每个响应添加安全相关的 HTTP 头"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Server"] = ""  # 隐藏服务器信息
    return response


# ==================== 速率限制 ====================

class RateLimiter:
    """基于 IP 的内存速率限制器。

    使用滑动窗口算法，每个 IP 一个窗口。
    """

    def __init__(self, requests: int = 100, window_seconds: int = 60):
        self.requests = requests
        self.window = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)
        # AI 接口更严格
        self._ai_limits: dict[str, tuple[int, int]] = {}  # path -> (requests, window)

    def set_ai_limit(self, path: str, requests: int, window: int):
        self._ai_limits[path] = (requests, window)

    def is_allowed(self, ip: str, path: str) -> bool:
        now = time.time()

        # AI 接口用更严格的限制
        limit, window = self.requests, self.window
        for ai_path, (ai_limit, ai_window) in self._ai_limits.items():
            if path.startswith(ai_path):
                limit, window = ai_limit, ai_window
                break

        # 清理过期记录
        timestamps = self._clients[ip]
        self._clients[ip] = [t for t in timestamps if now - t < window]

        if len(self._clients[ip]) >= limit:
            return False

        self._clients[ip].append(now)
        return True


# 全局实例：普通接口 100次/分钟，AI 接口 10次/分钟
_limiter = RateLimiter(requests=200, window_seconds=60)
_limiter.set_ai_limit("/api/ai/chat", 20, 60)
_limiter.set_ai_limit("/api/ai/sessions", 60, 60)


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """速率限制中间件"""
    ip = _get_client_ip(request)
    path = request.url.path

    if not _limiter.is_allowed(ip, path):
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试"},
        )

    return await call_next(request)


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP（兼容 Render 代理）"""
    # Render 通过 X-Forwarded-For 传递真实 IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # X-Real-IP 也是常见代理头
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


# ==================== 请求体大小限制 ====================

MAX_BODY_SIZE = 1 * 1024 * 1024  # 1 MB


async def body_size_limit_middleware(request: Request, call_next: Callable) -> Response:
    """限制请求体大小（防止大 payload 攻击）"""
    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={"detail": f"请求体过大，最大允许 {MAX_BODY_SIZE // 1024}KB"},
        )
    return await call_next(request)
