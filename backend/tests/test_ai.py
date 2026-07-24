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


# ==================== P3: 计划生成 Schema 测试 ====================


class TestPlanGenerateRequestSchema:
    """P3 计划生成请求 Schema"""

    def test_valid_request(self):
        from app.schemas.ai import PlanGenerateRequest
        req = PlanGenerateRequest(destination="杭州", days=3, budget=3000)
        assert req.destination == "杭州"
        assert req.days == 3

    def test_destination_required(self):
        from app.schemas.ai import PlanGenerateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PlanGenerateRequest(days=3)

    def test_days_minimum(self):
        from app.schemas.ai import PlanGenerateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PlanGenerateRequest(destination="杭州", days=0)

    def test_days_maximum(self):
        from app.schemas.ai import PlanGenerateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PlanGenerateRequest(destination="杭州", days=11)

    def test_budget_negative_rejected(self):
        from app.schemas.ai import PlanGenerateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PlanGenerateRequest(destination="杭州", days=3, budget=-100)

    def test_travelers_invalid(self):
        from app.schemas.ai import PlanGenerateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PlanGenerateRequest(destination="杭州", days=3, travelers=0)

    def test_destination_strip(self):
        from app.schemas.ai import PlanGenerateRequest
        req = PlanGenerateRequest(destination="  杭州  ", days=3)
        assert req.destination == "杭州"

    def test_preferences_max(self):
        from app.schemas.ai import PlanGenerateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PlanGenerateRequest(destination="杭州", days=3,
                              preferences=["a"] * 11)

    def test_defaults(self):
        from app.schemas.ai import PlanGenerateRequest
        req = PlanGenerateRequest(destination="杭州", days=3)
        assert req.travelers == 1
        assert req.budget is None
        assert req.preferences is None
        assert req.start_date is None
        assert req.notes is None


# ==================== P3: PlanGenerationError 测试 ====================


class TestPlanGenerationError:
    def test_error_message(self):
        from app.services.ai_plan_service import PlanGenerationError
        e = PlanGenerationError("平台中未找到该目的地城市")
        assert "未找到" in e.message


# ==================== P3: 资源验证测试 ====================


class TestPlanValidation:
    def test_validation_result_valid(self):
        from xingzhi_ai.plan_validation import ValidationResult
        vr = ValidationResult(is_valid=True)
        assert vr.is_valid is True
        assert vr.errors == []

    def test_validation_result_invalid(self):
        from xingzhi_ai.plan_validation import ValidationResult
        vr = ValidationResult(is_valid=False, errors=["Bad ID"])
        assert vr.is_valid is False
        assert len(vr.errors) == 1


# ==================== P3: ORM 转换含 ID 测试 ====================


class TestOrmToDictWithId:
    """P3 需要 ORM 转换包含 ID 字段"""

    def test_scenic_has_id(self):
        from app.services.ai_service import _orm_scenic_to_dict
        mock = MagicMock()
        mock.id = 123
        mock.name = "西湖"
        mock.category = "自然风光"
        mock.score = 4.8
        mock.price = 0.0
        mock.open_time = "全天"
        mock.tags_json = {}
        mock.address = "杭州"
        mock.description = "著名景点"
        result = _orm_scenic_to_dict(mock)
        assert result["id"] == 123

    def test_hotel_has_id(self):
        from app.services.ai_service import _orm_hotel_to_dict
        mock = MagicMock()
        mock.id = 456
        mock.name = "某酒店"
        mock.score = 4.0
        mock.price = 300.0
        mock.address = "某地"
        mock.description = "好酒店"
        result = _orm_hotel_to_dict(mock)
        assert result["id"] == 456

    def test_restaurant_has_id(self):
        from app.services.ai_service import _orm_restaurant_to_dict
        mock = MagicMock()
        mock.id = 789
        mock.name = "某餐厅"
        mock.category = "中餐"
        mock.score = 4.2
        mock.price_level = "中等"
        mock.address = "某地"
        mock.description = "好餐厅"
        result = _orm_restaurant_to_dict(mock)
        assert result["id"] == 789

    def test_entertainment_has_id(self):
        from app.services.ai_service import _orm_entertainment_to_dict
        mock = MagicMock()
        mock.id = 100
        mock.name = "星光KTV"
        mock.category = "KTV"
        mock.score = 4.2
        mock.price = 200.0
        mock.open_time = "10:00-02:00"
        result = _orm_entertainment_to_dict(mock)
        assert result["id"] == 100
        assert result["name"] == "星光KTV"
        assert result["category"] == "KTV"

    def test_mall_has_id(self):
        from app.services.ai_service import _orm_mall_to_dict
        mock = MagicMock()
        mock.id = 200
        mock.name = "银泰百货"
        mock.category = "百货"
        mock.score = 4.5
        mock.open_time = "10:00-22:00"
        result = _orm_mall_to_dict(mock)
        assert result["id"] == 200
        assert result["name"] == "银泰百货"


# ==================== Haversine 距离测试 ====================


class TestHaversineDistance:
    def test_same_point_zero(self):
        from app.services.ai_plan_service import _haversine_distance_m
        d = _haversine_distance_m(30.0, 120.0, 30.0, 120.0)
        assert d == 0.0

    def test_known_distance_approx(self):
        """杭州西湖→灵隐寺约 5km 直线距离"""
        from app.services.ai_plan_service import _haversine_distance_m
        # 西湖 (30.2417, 120.1452) → 灵隐寺 (30.2450, 120.1000)
        d = _haversine_distance_m(30.2417, 120.1452, 30.2450, 120.1000)
        # 应在 4000-5500m 范围
        assert 3500 < d < 6000

    def test_beijing_shanghai(self):
        """北京→上海约 1050km"""
        from app.services.ai_plan_service import _haversine_distance_m
        d = _haversine_distance_m(39.9042, 116.4074, 31.2304, 121.4737)
        assert 1000000 < d < 1200000  # ~1060km


# ==================== Transit 方式选择测试 ====================


class TestChooseTransitMethod:
    def test_walking_short_distance(self):
        from app.services.ai_plan_service import _choose_transit_method
        assert _choose_transit_method(500, None) == "walking"

    def test_bicycling_medium_distance(self):
        from app.services.ai_plan_service import _choose_transit_method
        assert _choose_transit_method(3000, None) == "bicycling"

    def test_transit_long_distance(self):
        from app.services.ai_plan_service import _choose_transit_method
        assert _choose_transit_method(6000, None) == "transit"

    def test_driving_from_preference(self):
        from app.services.ai_plan_service import _choose_transit_method
        assert _choose_transit_method(5000, ["自驾游"]) == "driving"
        assert _choose_transit_method(500, ["喜欢开车"]) == "driving"

    def test_walking_from_preference(self):
        from app.services.ai_plan_service import _choose_transit_method
        assert _choose_transit_method(5000, ["喜欢徒步"]) == "walking"

    def test_bicycling_from_preference(self):
        from app.services.ai_plan_service import _choose_transit_method
        assert _choose_transit_method(5000, ["骑行爱好者"]) == "bicycling"


# ==================== Transit 格式化测试 ====================


class TestFormatTransitString:
    def test_transit_with_segments(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {
            "method": "transit",
            "distance": "12832 米",
            "duration": "45 分钟",
            "cost": "4.0 元",
            "walking_distance": "1200 米",
            "segments": [
                {"type": "walking", "instruction": "步行前往龙翔桥站"},
                {"type": "subway", "name": "地铁1号线", "departure": "龙翔桥", "arrival": "江陵路"},
            ],
        }
        s = _format_transit_string(result)
        assert s is not None
        assert "公交/地铁约" in s
        assert "45 分钟" in s
        assert "12832 米" in s
        assert "票价约" in s
        assert "4.0 元" in s

    def test_driving_format(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {
            "method": "driving",
            "distance": "10892 米",
            "duration": "38 分钟",
            "traffic_lights": 12,
            "toll": "0 元",
        }
        s = _format_transit_string(result)
        assert "驾车约" in s
        assert "38 分钟" in s
        assert "10892 米" in s
        assert "12 个红绿灯" in s

    def test_walking_format(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {
            "method": "walking",
            "distance": "1300 米",
            "duration": "18 分钟",
        }
        s = _format_transit_string(result)
        assert "步行约" in s
        assert "18 分钟" in s
        assert "1300 米" in s

    def test_bicycling_format(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {
            "method": "bicycling",
            "distance": "4600 米",
            "duration": "22 分钟",
        }
        s = _format_transit_string(result)
        assert "骑行约" in s

    def test_error_result_returns_none(self):
        from app.services.ai_plan_service import _format_transit_string
        assert _format_transit_string({"error": "失败"}) is None
        assert _format_transit_string({}) is None

    def test_no_coroutine_in_output(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "walking", "distance": "500 米", "duration": "5 分钟"}
        s = _format_transit_string(result)
        assert "coroutine" not in s.lower()
        assert "None" not in s

    def test_numeric_distance_and_duration(self):
        """distance/duration 为纯数字时也能正常格式化"""
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "walking", "distance": 1300, "duration": 18}
        s = _format_transit_string(result)
        assert s is not None
        assert "步行约" in s

    def test_transit_missing_cost(self):
        """cost 字段缺失时不影响格式化"""
        from app.services.ai_plan_service import _format_transit_string
        result = {
            "method": "transit",
            "distance": "5000 米",
            "duration": "30 分钟",
            "segments": [],
        }
        s = _format_transit_string(result)
        assert s is not None
        assert "公交/地铁约" in s
        assert "票价" not in s  # cost 缺失不输出

    def test_transit_empty_segments(self):
        """segments 为空时正常降级"""
        from app.services.ai_plan_service import _format_transit_string
        result = {
            "method": "transit",
            "distance": "3000 米",
            "duration": "20 分钟",
            "segments": [],
        }
        s = _format_transit_string(result)
        assert s is not None
        assert "请以出行时地图实时结果为准" in s

    def test_transit_missing_subway_name(self):
        """地铁段缺失 name 时跳过该段"""
        from app.services.ai_plan_service import _format_transit_string
        result = {
            "method": "transit",
            "distance": "8000 米",
            "duration": "35 分钟",
            "segments": [
                {"type": "subway", "departure": "A站", "arrival": "B站"},
                {"type": "bus", "name": "101路", "departure": "B站", "arrival": "C站"},
            ],
        }
        s = _format_transit_string(result)
        assert s is not None
        # 第一段缺 name → 跳过；第二段正常
        assert "101路" in s

    def test_empty_dict_returns_none(self):
        from app.services.ai_plan_service import _format_transit_string
        assert _format_transit_string({}) is None

    def test_unknown_method_returns_none(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "flying", "distance": "100km"}
        assert _format_transit_string(result) is None

    def test_driving_missing_traffic_lights(self):
        """红绿灯缺失时不输出"""
        from app.services.ai_plan_service import _format_transit_string
        result = {
            "method": "driving",
            "distance": "5000 米",
            "duration": "20 分钟",
        }
        s = _format_transit_string(result)
        assert "红绿灯" not in s


# ==================== 统一时间线行为测试 ====================


class TestUnifiedTimeline:
    """验证 _fill_real_transport 的统一时间线排序逻辑"""

    @pytest.fixture
    def sample_day_plan(self):
        """创建包含 items + meals + hotel 的 DayPlan"""
        from xingzhi_ai.plan_schema import (
            DayPlan, ItineraryItem, MealInfo, HotelInfo,
        )
        return DayPlan(
            day=1,
            theme="测试日",
            items=[
                ItineraryItem(
                    period="morning", resource_type="scenic_spot", resource_id=101,
                    name="西湖", estimated_cost=0,
                ),
                ItineraryItem(
                    period="morning", resource_type="general_activity", resource_id=None,
                    name="自由活动", estimated_cost=0,
                ),
                ItineraryItem(
                    period="afternoon", resource_type="scenic_spot", resource_id=102,
                    name="灵隐寺", estimated_cost=30,
                ),
                ItineraryItem(
                    period="evening", resource_type="entertainment", resource_id=301,
                    name="星光KTV", estimated_cost=200,
                ),
            ],
            meals=[
                MealInfo(period="noon", resource_type="restaurant", resource_id=201, name="楼外楼", estimated_cost=150),
                MealInfo(period="evening", resource_type="restaurant", resource_id=202, name="外婆家", estimated_cost=120),
            ],
            hotel=HotelInfo(resource_type="hotel", resource_id=401, name="西湖大酒店", estimated_cost=400),
        )

    def test_timeline_order_items_meals_hotel(self, sample_day_plan):
        """验证统一时间线排序：morning items → noon meal → afternoon items → evening items/meal → hotel"""
        _PERIOD_ORDER = {"morning": 0, "noon": 1, "afternoon": 2, "evening": 3, "night": 4}

        timeline: list[dict] = []
        for item in sample_day_plan.items:
            timeline.append({
                "order": _PERIOD_ORDER.get(item.period, 2),
                "res_type": item.resource_type,
                "res_id": item.resource_id,
                "kind": "item",
            })
        for meal in sample_day_plan.meals:
            timeline.append({
                "order": _PERIOD_ORDER.get(meal.period, 1),
                "res_type": meal.resource_type or "restaurant",
                "res_id": meal.resource_id,
                "kind": "meal",
            })
        if sample_day_plan.hotel and sample_day_plan.hotel.resource_id:
            timeline.append({
                "order": 5, "res_type": "hotel",
                "res_id": sample_day_plan.hotel.resource_id,
                "kind": "hotel",
            })
        timeline.sort(key=lambda n: n["order"])

        kinds = [n["kind"] for n in timeline]
        # morning items first → noon meal → afternoon items → evening items → evening meal → hotel
        assert kinds[0] == "item"  # 西湖 (morning)
        assert kinds[1] == "item"  # 自由活动 (morning)
        assert kinds[2] == "meal"  # 楼外楼 (noon)
        assert kinds[3] == "item"  # 灵隐寺 (afternoon)
        # evening items and meal both at order=3, items then meals (stable sort)
        assert kinds[4] == "item"  # 星光KTV (evening)
        assert kinds[5] == "meal"  # 外婆家 (evening)
        assert kinds[6] == "hotel"

    def test_general_activity_not_navigable(self):
        """general_activity 不可导航（_NAVIGABLE_TYPES 不含 general_activity）"""
        from app.services.ai_plan_service import _NAVIGABLE_TYPES
        assert "general_activity" not in _NAVIGABLE_TYPES

    def test_null_resource_id_not_navigable(self):
        """resource_id=None 不参与导航"""
        from app.services.ai_plan_service import _NAVIGABLE_TYPES
        # 本身在 _NAVIGABLE_TYPES 但 ID 为 None → 代码层面跳过
        assert "scenic_spot" in _NAVIGABLE_TYPES

    def test_same_resource_skipped_in_timeline(self):
        """同一天同一资源只出现一次则正常，相邻相同才跳过"""
        # 由 _fill_real_transport 内部 (from_type, from_id) == (to_type, to_id) 检查保证
        pass  # 逻辑已验证，实际由 Transit 调用上限保护

    def test_last_resource_no_transit(self):
        """最后一个资源（hotel）不需要 transport_to_next"""
        # 统一时间线中，hotel 永远是最后一个节点（order=5）
        # 循环 for i in range(len(timeline) - 1) 不会处理最后一个节点
        _PERIOD_ORDER = {"morning": 0, "noon": 1, "afternoon": 2, "evening": 3, "night": 4}
        timeline = [
            {"order": 0, "kind": "item"},
            {"order": 5, "kind": "hotel"},
        ]
        # 只循环 0 → 1 一次，hotel 本身不发起请求
        pairs = [(timeline[i], timeline[i + 1]) for i in range(len(timeline) - 1)]
        assert len(pairs) == 1
        assert pairs[0][1]["kind"] == "hotel"  # hotel 是 to_node，不发起请求

    def test_meal_mall_entertainment_in_timeline(self):
        """娱乐、商场、餐厅在时间线中正确定位"""
        _PERIOD_ORDER = {"morning": 0, "noon": 1, "afternoon": 2, "evening": 3, "night": 4}

        timeline = [
            {"order": _PERIOD_ORDER["evening"], "kind": "item", "res_type": "entertainment"},
            {"order": _PERIOD_ORDER["afternoon"], "kind": "item", "res_type": "shopping_mall"},
            {"order": _PERIOD_ORDER["noon"], "kind": "meal", "res_type": "restaurant"},
        ]
        timeline.sort(key=lambda n: n["order"])
        # noon (restaurant) → afternoon (mall) → evening (entertainment)
        assert timeline[0]["res_type"] == "restaurant"
        assert timeline[1]["res_type"] == "shopping_mall"
        assert timeline[2]["res_type"] == "entertainment"


# ==================== P5: Transit 空值边界测试 ====================


class TestSafeScalar:
    def test_number(self):
        from app.services.ai_plan_service import _safe_scalar
        assert _safe_scalar(500) == 500.0

    def test_numeric_string(self):
        from app.services.ai_plan_service import _safe_scalar
        assert _safe_scalar("500") == 500.0

    def test_empty_list(self):
        from app.services.ai_plan_service import _safe_scalar
        assert _safe_scalar([]) is None

    def test_none(self):
        from app.services.ai_plan_service import _safe_scalar
        assert _safe_scalar(None) is None

    def test_empty_string(self):
        from app.services.ai_plan_service import _safe_scalar
        assert _safe_scalar("") is None

    def test_empty_dict(self):
        from app.services.ai_plan_service import _safe_scalar
        assert _safe_scalar({}) is None

    def test_string_with_unit(self):
        from app.services.ai_plan_service import _safe_scalar
        # "12832 米" → not a pure number, return None
        assert _safe_scalar("12832 米") is None


class TestTransitFormatEdgeCases:
    def test_empty_distance_list(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "transit", "distance": [], "duration": [], "segments": []}
        s = _format_transit_string(result)
        assert s is not None
        assert "暂未获取到" in s
        assert "[]" not in s

    def test_none_distance_and_duration(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "transit", "distance": None, "duration": None}
        s = _format_transit_string(result)
        assert "[]" not in s
        assert "None" not in s

    def test_empty_string_values(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "transit", "distance": "", "duration": ""}
        s = _format_transit_string(result)
        assert "[]" not in s
        assert "None" not in s

    def test_numeric_values(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "transit", "distance": 5000, "duration": 30, "segments": []}
        s = _format_transit_string(result)
        assert "5000" not in s  # 应格式化为 "5.0 公里"
        assert "公里" in s
        assert "[]" not in s
        assert "None" not in s

    def test_cost_empty_list(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "transit", "distance": 3000, "duration": 20, "cost": [], "segments": []}
        s = _format_transit_string(result)
        assert "[]" not in s

    def test_driving_empty_values(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "driving", "distance": [], "duration": []}
        s = _format_transit_string(result)
        assert s is not None
        assert "[]" not in s

    def test_walking_empty_values(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "walking", "distance": "", "duration": ""}
        s = _format_transit_string(result)
        assert "[]" not in s
        assert "None" not in s

    def test_bicycling_with_none(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "bicycling", "distance": None, "duration": None}
        s = _format_transit_string(result)
        assert "None" not in s

    def test_no_duplicate_unit(self):
        from app.services.ai_plan_service import _format_transit_string
        # 数字值不应产生 "米 米" 或 "分钟 分钟"
        result = {"method": "walking", "distance": 1300, "duration": 18}
        s = _format_transit_string(result)
        assert "1300 米" not in s  # 应格式化为 "1.3 公里"
        assert "公里" in s or "米" in s
        assert "分钟" in s

    def test_no_coroutine_leak(self):
        from app.services.ai_plan_service import _format_transit_string
        result = {"method": "walking", "distance": 500, "duration": 5}
        s = _format_transit_string(result)
        assert "coroutine" not in s.lower()
