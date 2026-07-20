"""
行知 AI 核心包 — DeepSeek 客户端、Prompt 模板、上下文管理

导入方式:
    from xingzhi_ai.client import DeepSeekChatClient
    from xingzhi_ai.prompts import build_system_prompt
    from xingzhi_ai.context import ChatMessage, trim_context
    from xingzhi_ai.exceptions import (
        AIServiceError,
        AIConfigurationError,
        AIUpstreamError,
        AIEmptyResponseError,
    )
"""

from xingzhi_ai.exceptions import (
    AIServiceError,
    AIConfigurationError,
    AIUpstreamError,
    AIEmptyResponseError,
)
from xingzhi_ai.types import ChatMessage
from xingzhi_ai.client import DeepSeekChatClient
from xingzhi_ai.prompts import build_system_prompt
from xingzhi_ai.context import (
    filter_valid_messages,
    trim_context,
    build_messages_with_system_prompt,
)

__all__ = [
    # Exceptions
    "AIServiceError",
    "AIConfigurationError",
    "AIUpstreamError",
    "AIEmptyResponseError",
    # Types
    "ChatMessage",
    # Client
    "DeepSeekChatClient",
    # Prompts
    "build_system_prompt",
    # Context
    "filter_valid_messages",
    "trim_context",
    "build_messages_with_system_prompt",
]
