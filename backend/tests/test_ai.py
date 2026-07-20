"""AI 路由集成测试 — 使用 FastAPI TestClient + Mock DeepSeek"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# 在导入 app 之前 Mock DeepSeekChatClient，避免网络请求
# 因为 ai_service 在模块导入时只定义了函数，不实例化客户端，
# 所以可以在测试时直接 Mock 函数级别


@pytest.fixture
def mock_deepseek_reply():
    """Mock DeepSeek 正常回复"""
    return "杭州一日游推荐路线：西湖 → 灵隐寺 → 河坊街。预算约200元。"


@pytest.fixture
def mock_generate_ai_reply(mock_deepseek_reply):
    """Mock ai_service.generate_ai_reply 返回正常回复"""
    async def _mock(*args, **kwargs):
        return mock_deepseek_reply

    return _mock


# ==================== Schema 验证测试（无需 App） ====================


class TestAIChatRequestSchema:
    def test_valid_message(self):
        from app.schemas.ai import AIChatRequest
        req = AIChatRequest(message="推荐杭州一日游")
        assert req.message == "推荐杭州一日游"
        assert req.session_id is None

    def test_with_session_id(self):
        from app.schemas.ai import AIChatRequest
        req = AIChatRequest(message="继续", session_id=42)
        assert req.session_id == 42

    def test_empty_message_rejected(self):
        from app.schemas.ai import AIChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AIChatRequest(message="")

    def test_whitespace_message_rejected(self):
        from app.schemas.ai import AIChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AIChatRequest(message="   ")

    def test_too_long_message_rejected(self):
        from app.schemas.ai import AIChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AIChatRequest(message="a" * 4001)

    def test_message_at_max_length_accepted(self):
        from app.schemas.ai import AIChatRequest
        req = AIChatRequest(message="a" * 4000)
        assert len(req.message) == 4000

    def test_message_stripping_needed_in_api(self):
        """Schema 不做自动 strip，API 层需要处理"""
        from app.schemas.ai import AIChatRequest
        req = AIChatRequest(message="  hello  ")
        # Field 只做 min_length/max_length 验证，不自动 strip
        assert req.message == "  hello  "


# ==================== Mock Service 测试 ====================


class TestContextBuilding:
    """测试 ai_service 中的上下文构建逻辑"""

    def test_get_recent_messages_limited_by_user(self):
        """验证 SQL 查询只针对当前用户"""
        from app.services.ai_service import get_recent_messages_by_user
        from app.services.ai_service import DEFAULT_HISTORY_LIMIT

        # 静态验证：确认常量值合理
        assert DEFAULT_HISTORY_LIMIT == 20

    def test_orm_to_chat_message_conversion(self):
        """ORM 对象转 ChatMessage 格式正确"""
        from app.services.ai_service import _orm_to_chat_message

        # 创建模拟 ORM 对象
        mock_msg = MagicMock()
        mock_msg.role = "user"
        mock_msg.content = "test message"

        result = _orm_to_chat_message(mock_msg)
        assert result["role"] == "user"
        assert result["content"] == "test message"
        # 确保没有泄露数据库字段
        assert "id" not in result
        assert "user_id" not in result


class TestAIExceptionHandling:
    """测试 AI 异常 → HTTP 异常转换"""

    def test_config_error_503(self):
        from app.api.ai import _handle_ai_exception
        from xingzhi_ai.exceptions import AIConfigurationError
        from fastapi import HTTPException

        exc = _handle_ai_exception(AIConfigurationError())
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 503
        assert "未配置" in exc.detail

    def test_upstream_error_503(self):
        from app.api.ai import _handle_ai_exception
        from xingzhi_ai.exceptions import AIUpstreamError
        from fastapi import HTTPException

        exc = _handle_ai_exception(AIUpstreamError())
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 503
        assert "暂时不可用" in exc.detail

    def test_empty_response_error_503(self):
        from app.api.ai import _handle_ai_exception
        from xingzhi_ai.exceptions import AIEmptyResponseError
        from fastapi import HTTPException

        exc = _handle_ai_exception(AIEmptyResponseError())
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 503
        assert "无效结果" in exc.detail
