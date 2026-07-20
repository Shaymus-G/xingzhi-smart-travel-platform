"""AI 层专用异常 — 不依赖 FastAPI 的 HTTPException"""


class AIServiceError(Exception):
    """AI 服务通用异常基类"""

    def __init__(self, message: str = "AI 服务错误"):
        self.message = message
        super().__init__(message)


class AIConfigurationError(AIServiceError):
    """AI 配置错误（如 API Key 未配置）"""

    def __init__(self, message: str = "AI 服务未配置"):
        super().__init__(message)


class AIUpstreamError(AIServiceError):
    """上游 AI 服务错误（网络、超时、API 异常）"""

    def __init__(self, message: str = "AI 服务暂时不可用"):
        super().__init__(message)


class AIEmptyResponseError(AIServiceError):
    """AI 返回空内容"""

    def __init__(self, message: str = "AI 服务返回了无效结果"):
        super().__init__(message)
