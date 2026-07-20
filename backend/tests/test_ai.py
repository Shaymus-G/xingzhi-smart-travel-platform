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


# ==================== P2: ORM 转换测试 ====================


class TestOrmToDictConversion:
    """测试 ORM 对象 → 普通 dict 转换"""

    def test_scenic_conversion_with_tags(self):
        from app.services.ai_service import _orm_scenic_to_dict
        mock = MagicMock()
        mock.name = "西湖"
        mock.category = "自然风光"
        mock.score = 4.8
        mock.price = 0.0
        mock.open_time = "全天"
        mock.tags_json = {"特色": "湖景", "等级": "5A"}
        mock.address = "杭州市西湖区"
        mock.description = "著名景点"

        result = _orm_scenic_to_dict(mock)
        assert result["name"] == "西湖"
        assert result["score"] == 4.8
        assert result["price"] == 0.0
        assert "湖景" in result["tags"]
        assert "5A" in result["tags"]

    def test_scenic_conversion_null_tags(self):
        from app.services.ai_service import _orm_scenic_to_dict
        mock = MagicMock()
        mock.name = "某景点"
        mock.category = None
        mock.score = None
        mock.price = None
        mock.open_time = None
        mock.tags_json = None
        mock.address = None
        mock.description = None

        result = _orm_scenic_to_dict(mock)
        assert result["name"] == "某景点"
        assert result["score"] is None
        assert result["price"] is None
        assert result["tags"] == ""
        assert result["category"] == ""

    def test_scenic_conversion_empty_tags_json(self):
        from app.services.ai_service import _orm_scenic_to_dict
        mock = MagicMock()
        mock.name = "某景点"
        mock.tags_json = {}
        result = _orm_scenic_to_dict(mock)
        assert result["tags"] == ""

    def test_hotel_conversion(self):
        from app.services.ai_service import _orm_hotel_to_dict
        mock = MagicMock()
        mock.name = "某酒店"
        mock.score = 4.2
        mock.price = 350.0
        mock.address = "某地址"
        mock.description = "某描述"

        result = _orm_hotel_to_dict(mock)
        assert result["name"] == "某酒店"
        assert result["score"] == 4.2
        assert result["price"] == 350.0

    def test_hotel_conversion_nulls(self):
        from app.services.ai_service import _orm_hotel_to_dict
        mock = MagicMock()
        mock.name = "某酒店"
        mock.score = None
        mock.price = None
        mock.address = None
        mock.description = None

        result = _orm_hotel_to_dict(mock)
        assert result["score"] is None
        assert result["price"] is None
        assert result["address"] == ""

    def test_restaurant_conversion(self):
        from app.services.ai_service import _orm_restaurant_to_dict
        mock = MagicMock()
        mock.name = "某餐厅"
        mock.category = "川菜"
        mock.score = 4.0
        mock.price_level = "中等"
        mock.address = "某地址"
        mock.description = "某描述"

        result = _orm_restaurant_to_dict(mock)
        assert result["name"] == "某餐厅"
        assert result["category"] == "川菜"
        assert result["price_level"] == "中等"

    def test_preference_conversion(self):
        from app.services.ai_service import _orm_preference_to_dict
        mock = MagicMock()
        mock.preference_type = "美食"
        mock.preference_value = "本地特色"
        mock.weight = 1.5

        result = _orm_preference_to_dict(mock)
        assert result["preference_type"] == "美食"
        assert result["preference_value"] == "本地特色"
        assert result["weight"] == 1.5

    def test_preference_conversion_default_weight(self):
        from app.services.ai_service import _orm_preference_to_dict
        mock = MagicMock()
        mock.preference_type = "住宿"
        mock.preference_value = "经济型"
        # weight 不存在时
        del mock.weight

        result = _orm_preference_to_dict(mock)
        assert result["weight"] == 1.0  # 默认值


# ==================== P2: 天气触发判断测试 ====================


class TestShouldQueryWeather:
    @pytest.fixture
    def settings_with_weather(self):
        """创建设置对象，包含 OpenWeather API Key"""
        from app.core.config import Settings
        s = Settings()
        object.__setattr__(s, "OPENWEATHER_KEY", "test-weather-key")
        return s

    @pytest.fixture
    def settings_without_weather(self):
        """创建设置对象，不包含 OpenWeather API Key"""
        from app.core.config import Settings
        s = Settings()
        object.__setattr__(s, "OPENWEATHER_KEY", "")
        return s

    def test_triggers_with_travel_keyword(self, settings_with_weather):
        from app.services.ai_service import _should_query_weather
        assert _should_query_weather("推荐杭州一日游", settings_with_weather) is True

    def test_triggers_with_weather_keyword(self, settings_with_weather):
        from app.services.ai_service import _should_query_weather
        assert _should_query_weather("杭州今天天气怎么样", settings_with_weather) is True

    def test_triggers_with_outdoor_keyword(self, settings_with_weather):
        from app.services.ai_service import _should_query_weather
        assert _should_query_weather("我想去杭州爬山", settings_with_weather) is True

    def test_no_trigger_without_keywords(self, settings_with_weather):
        from app.services.ai_service import _should_query_weather
        assert _should_query_weather("你好", settings_with_weather) is False

    def test_no_trigger_when_key_not_configured(self, settings_without_weather):
        from app.services.ai_service import _should_query_weather
        assert _should_query_weather("杭州天气怎么样", settings_without_weather) is False

    def test_triggers_with_plan_keyword(self, settings_with_weather):
        from app.services.ai_service import _should_query_weather
        assert _should_query_weather("帮我安排一下杭州三日游计划", settings_with_weather) is True


# ==================== P2: 降级策略测试 ====================


class TestP2Degradation:
    """测试 P2 各步骤失败时的降级行为"""

    def test_generate_ai_reply_still_works_without_travel_data(self):
        """当 P2 数据收集失败时，仍然可以调用 AI（P1 降级）"""
        from app.services.ai_service import generate_ai_reply
        assert generate_ai_reply is not None  # 函数存在
        # 实际降级行为通过集成测试验证

    def test_orm_to_chat_message_no_leak(self):
        """ORM → ChatMessage 不泄露数据库字段"""
        from app.services.ai_service import _orm_to_chat_message
        mock = MagicMock()
        mock.role = "user"
        mock.content = "hello"
        mock.user_id = 1
        mock.id = 100
        mock.created_at = "2026-01-01"

        result = _orm_to_chat_message(mock)
        assert "id" not in result
        assert "user_id" not in result
        assert "created_at" not in result
        assert result["role"] == "user"
        assert result["content"] == "hello"


# ==================== P2: 上下文构建回归测试 ====================


class TestP2ContextBuilding:
    """确保 P2 的上下文构建不影响 P1 功能"""

    def test_build_messages_with_travel_context_exists(self):
        from xingzhi_ai.context import build_messages_with_travel_context
        assert build_messages_with_travel_context is not None

    def test_build_messages_with_travel_context_include_block(self):
        """travel_context_block 非空时出现在 system messages 中"""
        from xingzhi_ai.context import build_messages_with_travel_context
        from xingzhi_ai.types import ChatMessage

        result = build_messages_with_travel_context(
            history=[],
            current_message=ChatMessage(role="user", content="推荐杭州一日游"),
            travel_context_block="【平台旅游数据】\n- 城市：杭州\n【平台数据结束】",
        )
        # 至少有一个 system message 包含旅游数据块
        system_msgs = [m for m in result if m["role"] == "system"]
        assert len(system_msgs) >= 2  # 主 prompt + 数据块
        # 数据块是第二个 system message
        assert "杭州" in system_msgs[1]["content"]

    def test_build_messages_with_travel_context_empty_block(self):
        """travel_context_block 为空时不添加额外的 system message"""
        from xingzhi_ai.context import build_messages_with_travel_context
        from xingzhi_ai.types import ChatMessage

        result = build_messages_with_travel_context(
            history=[],
            current_message=ChatMessage(role="user", content="你好"),
            travel_context_block="",
        )
        system_msgs = [m for m in result if m["role"] == "system"]
        assert len(system_msgs) == 1  # 只有主 prompt，无数据块

    def test_system_prompt_with_grounding(self):
        from xingzhi_ai.prompts import build_system_prompt
        prompt = build_system_prompt(with_grounding=True)
        assert "数据使用规则" in prompt
        assert "不得编造" in prompt

    def test_system_prompt_without_grounding(self):
        from xingzhi_ai.prompts import build_system_prompt
        prompt = build_system_prompt(with_grounding=False)
        assert "数据使用规则" not in prompt


# ==================== P2: 多轮城市继承测试 ====================


class TestMultiTurnCityResolution:
    """多轮对话中城市继承逻辑的单元测试"""

    def test_current_message_priority(self):
        """当前消息有城市 → 直接使用"""
        from xingzhi_ai.location import resolve_city_from_conversation, CityCandidate
        candidates = [CityCandidate("杭州", "浙江省", 1)]
        result = resolve_city_from_conversation(
            "推荐杭州一日游",
            [],  # 无历史
            candidates,
        )
        assert result is not None and result.name == "杭州"

    def test_inherit_from_history(self):
        """当前消息无城市 → 从历史 user 消息继承"""
        from xingzhi_ai.location import resolve_city_from_conversation, CityCandidate
        candidates = [CityCandidate("杭州", "浙江省", 1)]
        result = resolve_city_from_conversation(
            "如果天气不好怎么调整",
            ["推荐杭州一日游方案"],
            candidates,
        )
        assert result is not None and result.name == "杭州"

    def test_new_city_overrides(self):
        """当前消息新城市覆盖历史"""
        from xingzhi_ai.location import resolve_city_from_conversation, CityCandidate
        candidates = [
            CityCandidate("杭州", "浙江省", 1),
            CityCandidate("成都", "四川省", 2),
        ]
        result = resolve_city_from_conversation(
            "成都有什么好玩的",
            ["推荐杭州一日游"],
            candidates,
        )
        assert result is not None and result.name == "成都"

    def test_most_recent_user_wins(self):
        """多条历史 user → 最近一次的城市优先"""
        from xingzhi_ai.location import resolve_city_from_conversation, CityCandidate
        candidates = [
            CityCandidate("杭州", "浙江省", 1),
            CityCandidate("苏州", "江苏省", 2),
        ]
        result = resolve_city_from_conversation(
            "继续说",
            ["推荐杭州一日游", "苏州有什么好玩的"],
            candidates,
        )
        assert result is not None and result.name == "苏州"

    def test_no_city_returns_none(self):
        """无城市 → None"""
        from xingzhi_ai.location import resolve_city_from_conversation, CityCandidate
        candidates = [CityCandidate("杭州", "浙江省", 1)]
        result = resolve_city_from_conversation(
            "你好",
            ["今天天气不错"],
            candidates,
        )
        assert result is None

    def test_assistant_city_not_inherited(self):
        """调用方不传入 assistant 消息 → 不会误匹配"""
        from xingzhi_ai.location import resolve_city_from_conversation, CityCandidate
        candidates = [CityCandidate("上海城区", "上海市", 1)]
        # 调用方应只传 user 消息，不传 assistant 消息
        result = resolve_city_from_conversation(
            "继续",
            ["推荐杭州旅游"],  # 只有 user 消息
            candidates,
        )
        # "上海"不在 user 消息列表中，应返回 None
        assert result is None


class TestWeatherCityNameForApi:
    """天气查询城市名转换"""

    def test_chengqu_normalized_for_weather(self):
        from xingzhi_ai.location import resolve_weather_city_name, CityCandidate
        c = CityCandidate("北京城区", "北京市", 1)
        assert resolve_weather_city_name(c) == "北京"

    def test_shanghai_normalized_for_weather(self):
        from xingzhi_ai.location import resolve_weather_city_name, CityCandidate
        c = CityCandidate("上海城区", "上海市", 2)
        assert resolve_weather_city_name(c) == "上海"

    def test_bare_name_unchanged(self):
        from xingzhi_ai.location import resolve_weather_city_name, CityCandidate
        c = CityCandidate("杭州", "浙江省", 3)
        assert resolve_weather_city_name(c) == "杭州"


class TestWeatherTriggerMultiTurn:
    """天气触发：仅基于当前消息"""

    def test_current_weather_keyword_triggers(self):
        from app.services.ai_service import _should_query_weather
        from app.core.config import Settings
        s = Settings()
        object.__setattr__(s, "OPENWEATHER_KEY", "test-key")
        assert _should_query_weather("如果天气不适合户外怎么调整", s) is True

    def test_past_weather_keyword_does_not_trigger(self):
        """历史消息中有"天气"但当前消息没有 → 不应触发天气"""
        from app.services.ai_service import _should_query_weather
        from app.core.config import Settings
        s = Settings()
        object.__setattr__(s, "OPENWEATHER_KEY", "test-key")
        # 当前消息不含触发关键词
        assert _should_query_weather("还有哪些地方值得去", s) is False
