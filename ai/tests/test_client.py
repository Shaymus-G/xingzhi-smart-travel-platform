"""DeepSeek 客户端单元测试 — 使用 Mock，不调用真实 API"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from xingzhi_ai.client import DeepSeekChatClient
from xingzhi_ai.exceptions import (
    AIConfigurationError,
    AIUpstreamError,
    AIEmptyResponseError,
)
from xingzhi_ai.types import ChatMessage


# ==================== 构造测试 ====================


class TestClientInit:
    def test_empty_api_key_raises(self):
        with pytest.raises(AIConfigurationError):
            DeepSeekChatClient(api_key="")

    def test_whitespace_api_key_raises(self):
        with pytest.raises(AIConfigurationError):
            DeepSeekChatClient(api_key="   ")

    def test_valid_key_creates_instance(self):
        client = DeepSeekChatClient(api_key="sk-test-key")
        assert client.model == "deepseek-chat"

    def test_custom_model(self):
        client = DeepSeekChatClient(api_key="sk-test", model="deepseek-reasoner")
        assert client.model == "deepseek-reasoner"

    def test_custom_base_url(self):
        client = DeepSeekChatClient(api_key="sk-test", base_url="https://custom.api")
        # 不暴露 client 内部属性，仅验证不抛异常
        assert client is not None


# ==================== chat 测试（Mock） ====================


@pytest.fixture
def client():
    return DeepSeekChatClient(api_key="sk-test-key")


@pytest.fixture
def sample_messages() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="You are a travel assistant."),
        ChatMessage(role="user", content="推荐杭州一日游"),
    ]


class TestChatNormal:
    def test_returns_reply_text(self, client, sample_messages):
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="杭州一日游推荐：西湖 → 灵隐寺 → 河坊街"))
        ]

        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        import asyncio

        with patch.object(client, "_client", mock_async_client):
            reply = asyncio.run(client.chat(sample_messages))
        assert "杭州" in reply
        assert len(reply) > 0


class TestChatErrors:
    def test_empty_choices_raises(self, client, sample_messages):
        mock_completion = MagicMock()
        mock_completion.choices = []

        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        with patch.object(client, "_client", mock_async_client):
            import asyncio
            with pytest.raises(AIEmptyResponseError):
                asyncio.run(client.chat(sample_messages))

    def test_none_content_raises(self, client, sample_messages):
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content=None))
        ]

        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        with patch.object(client, "_client", mock_async_client):
            import asyncio
            with pytest.raises(AIEmptyResponseError):
                asyncio.run(client.chat(sample_messages))

    def test_empty_content_raises(self, client, sample_messages):
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="   "))
        ]

        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        with patch.object(client, "_client", mock_async_client):
            import asyncio
            with pytest.raises(AIEmptyResponseError):
                asyncio.run(client.chat(sample_messages))

    def test_sdk_exception_converts_to_upstream_error(self, client, sample_messages):
        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        with patch.object(client, "_client", mock_async_client):
            import asyncio
            with pytest.raises(AIUpstreamError) as exc_info:
                asyncio.run(client.chat(sample_messages))
            assert "暂时不可用" in exc_info.value.message

    def test_timeout_converts_to_upstream_error(self, client, sample_messages):
        import asyncio
        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=asyncio.TimeoutError("timeout")
        )

        with patch.object(client, "_client", mock_async_client):
            with pytest.raises(AIUpstreamError):
                asyncio.run(client.chat(sample_messages))


class TestChatNoApiKeyLeak:
    """确保异常信息中不包含 API Key"""

    def test_error_message_no_api_key_leak(self, client, sample_messages):
        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=Exception("sk-test-key leaked?")
        )

        with patch.object(client, "_client", mock_async_client):
            import asyncio
            with pytest.raises(AIUpstreamError) as exc_info:
                asyncio.run(client.chat(sample_messages))
            # 用户可见的错误信息不应包含原始异常文本中的 Key
            assert "sk-test-key" not in exc_info.value.message
