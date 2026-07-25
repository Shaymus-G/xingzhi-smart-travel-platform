"""DeepSeek 异步聊天客户端 — 基于 OpenAI Python SDK 兼容接口

不依赖 FastAPI / SQLAlchemy，可独立测试。
"""

from __future__ import annotations

import logging
from openai import AsyncOpenAI

from xingzhi_ai.exceptions import (
    AIConfigurationError,
    AIUpstreamError,
    AIEmptyResponseError,
)
from xingzhi_ai.types import ChatMessage

logger = logging.getLogger(__name__)


class DeepSeekChatClient:
    """DeepSeek 异步聊天客户端。

    Usage::

        client = DeepSeekChatClient(api_key="sk-...")
        reply = await client.chat([
            {"role": "system", "content": "你是旅行助手"},
            {"role": "user", "content": "推荐杭州玩法"},
        ])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        timeout_seconds: float = 30.0,
    ):
        if not api_key or not api_key.strip():
            raise AIConfigurationError("AI 服务未配置，请联系管理员")

        self._model = model
        self._timeout = timeout_seconds

        self._client = AsyncOpenAI(
            api_key=api_key.strip(),
            base_url=base_url,
            timeout=timeout_seconds,
        )

    @property
    def model(self) -> str:
        return self._model

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        """调用 DeepSeek Chat API 并返回助手回复文本。

        Args:
            messages: 完整的消息列表（含 system / 历史 / 当前用户）。
            temperature: 生成温度，默认 0.7（普通聊天），计划生成建议 0.1-0.3。
            max_tokens: 最大输出 token 数，None 使用 API 默认值。
            response_format: OpenAI 兼容的 response_format 参数，
                例如 {"type": "json_object"}。

        Returns:
            助手回复文本（已去除首尾空白）。

        Raises:
            AIUpstreamError: 网络错误、超时或 API 返回错误。
            AIEmptyResponseError: API 返回空 choices 或空 content。
        """
        # 构建 API 兼容的消息格式（排除 role 之外的可能多余字段）
        api_messages: list[dict[str, str]] = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

        # 构建 API 调用参数
        api_kwargs: dict = {
            "model": self._model,
            "messages": api_messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            api_kwargs["max_tokens"] = max_tokens
        if response_format is not None:
            api_kwargs["response_format"] = response_format

        try:
            completion = await self._client.chat.completions.create(**api_kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            # 将 OpenAI SDK / 网络 / 超时异常统一转换
            # 不在异常信息中包含原始请求详情
            logger.error(
                "DeepSeek API 调用失败: %s: %s",
                type(exc).__name__,
                str(exc)[:500],
            )
            raise AIUpstreamError("AI 服务暂时不可用，请稍后再试") from exc

        # 检查 choices
        if not completion.choices:
            logger.error("DeepSeek 返回空 choices")
            raise AIEmptyResponseError("AI 服务返回了无效结果，请稍后再试")

        content = completion.choices[0].message.content

        if content is None:
            logger.error("DeepSeek 返回 content 为 None")
            raise AIEmptyResponseError("AI 服务返回了无效结果，请稍后再试")

        stripped = content.strip()
        if not stripped:
            logger.error("DeepSeek 返回空 content")
            raise AIEmptyResponseError("AI 服务返回了无效结果，请稍后再试")

        return stripped
