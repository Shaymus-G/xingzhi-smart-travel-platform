"""AI 包通用类型定义 — 轻量，不引入复杂模型框架"""

from typing import Literal, TypedDict


class ChatMessage(TypedDict):
    """单条聊天消息，兼容 OpenAI Chat Completions API 格式"""
    role: Literal["system", "user", "assistant"]
    content: str
