"""
行知 AI 核心包 — DeepSeek 客户端、Prompt 模板、上下文管理、城市识别、旅游数据

导入方式:
    from xingzhi_ai.client import DeepSeekChatClient
    from xingzhi_ai.prompts import build_system_prompt
    from xingzhi_ai.context import ChatMessage, trim_context, build_messages_with_travel_context
    from xingzhi_ai.location import CityCandidate, find_mentioned_city, normalize_city_name
    from xingzhi_ai.travel_context import TravelContext, build_travel_context_block
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
    build_messages_with_travel_context,
)
from xingzhi_ai.location import (
    CityCandidate,
    normalize_city_name,
    find_mentioned_city,
    resolve_city_from_conversation,
    resolve_weather_city_name,
)
from xingzhi_ai.travel_context import (
    ScenicInfo,
    HotelInfo,
    RestaurantInfo,
    EntertainmentInfo,
    ShoppingMallInfo,
    PreferenceInfo,
    WeatherInfo,
    TravelContext,
    build_travel_context_block,
    classify_entertainment_subtype,
    classify_mall_subtype,
    detect_user_intents,
    score_entertainment_candidate,
    score_mall_candidate,
    filter_and_rank_entertainments,
    filter_and_rank_malls,
)

# P3: 旅行计划生成
from xingzhi_ai.plan_schema import StructuredTravelPlan
from xingzhi_ai.plan_parser import extract_and_parse_json, PlanParseError
from xingzhi_ai.plan_validation import validate_plan_resources, ValidationResult
from xingzhi_ai.plan_renderer import render_travel_plan_markdown
from xingzhi_ai.plan_prompts import build_plan_system_prompt

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
    "build_messages_with_travel_context",
    # Location
    "CityCandidate",
    "normalize_city_name",
    "find_mentioned_city",
    "resolve_city_from_conversation",
    "resolve_weather_city_name",
    # Travel Context
    "ScenicInfo",
    "HotelInfo",
    "RestaurantInfo",
    "EntertainmentInfo",
    "ShoppingMallInfo",
    "PreferenceInfo",
    "WeatherInfo",
    "TravelContext",
    "build_travel_context_block",
    "classify_entertainment_subtype",
    "classify_mall_subtype",
    "detect_user_intents",
    "score_entertainment_candidate",
    "score_mall_candidate",
    "filter_and_rank_entertainments",
    "filter_and_rank_malls",
    # P3: Plan Generation
    "StructuredTravelPlan",
    "extract_and_parse_json",
    "PlanParseError",
    "validate_plan_resources",
    "ValidationResult",
    "render_travel_plan_markdown",
    "build_plan_system_prompt",
]
