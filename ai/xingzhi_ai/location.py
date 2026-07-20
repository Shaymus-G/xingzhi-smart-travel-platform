"""城市识别 — 基于规则的城市名匹配。

纯函数，不依赖数据库或外部服务，可独立测试。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class CityCandidate:
    """城市候选 — AI 包与后端之间的轻量数据传输。

    不包含 ORM 内部字段，只保留匹配和显示所需的信息。
    """

    name: str
    province: str
    city_id: int
    # 原始数据库名称（可能含"城区"等后缀），用于标准化显示
    display_name: str = field(default="")

    def __post_init__(self):
        if not self.display_name:
            object.__setattr__(self, "display_name", self.name)


# 常见行政区划后缀，按长度降序（优先匹配长后缀）
_SUFFIXES_TO_STRIP: tuple[str, ...] = (
    "自治州",
    "城区",     # 北京城区 → 北京
    "地区",
    "市",
    "县",
    "区",
    "盟",
)

# 需要保留后缀的特殊城市名（此处"州"是名称本体的一部分）
# 例如：杭州、苏州、广州中的"州"不应被剥离
# 当前后缀列表不包含单字"州"，因此不会误剥离


def normalize_city_name(name: str) -> str:
    """标准化城市名称：去除常见行政区划后缀。

    规则（按顺序）：
    1. 去除尾部空白
    2. 尝试剥离最长匹配的行政区划后缀
    3. 单字"州"、单字"盟"等不剥离（它们在城市名中是本体）

    Args:
        name: 用户输入或数据库中的原始城市名。

    Returns:
        标准化后的城市名（不保证存在于数据库中）。

    Examples:
        >>> normalize_city_name("杭州市")
        '杭州'
        >>> normalize_city_name("杭州")
        '杭州'
        >>> normalize_city_name("北京城区")
        '北京'
        >>> normalize_city_name("湘西土家族苗族自治州")
        '湘西土家族苗族'
        >>> normalize_city_name("长沙县")
        '长沙'
    """
    name = name.strip()
    for suffix in _SUFFIXES_TO_STRIP:
        if name.endswith(suffix) and len(name) > len(suffix):
            # 确保剥离后仍保留有意义的部分
            stripped = name[: -len(suffix)]
            if len(stripped) >= 1:
                return stripped
    return name


def find_mentioned_city(
    user_text: str,
    city_candidates: list[CityCandidate],
) -> Optional[CityCandidate]:
    """在用户消息中识别提到的城市。

    匹配策略（确定性，不调用 LLM）：
    1. 对候选城市按名称长度降序排列（最长优先，避免"江"匹配到"江门"）
    2. 对每个候选，尝试：
       a. 原始城市名精确子串匹配（用户说"杭州" → 匹配"杭州"）
       b. 标准化后的城市名匹配（用户说"杭州市" → normalize → "杭州" → 匹配）
       c. 对含"城区"的城市名，额外尝试其 normalized 形式（用户说"北京" →
          normalize("北京城区")="北京" → 匹配）
    3. 最先命中的就是结果（已按长度降序，天然最长优先）
    4. 不进行模糊匹配（不把"江苏"匹配到"江门"）

    Args:
        user_text: 用户当前消息文本。
        city_candidates: 数据库中所有城市候选列表。

    Returns:
        匹配到的 CityCandidate，如果没有则返回 None。
    """
    if not user_text or not city_candidates:
        return None

    # 按名称长度降序：最长优先，避免短名称抢先匹配
    sorted_candidates = sorted(
        city_candidates,
        key=lambda c: len(c.name),
        reverse=True,
    )

    for candidate in sorted_candidates:
        # 方式 a：原始名称精确子串匹配
        if candidate.name in user_text:
            return candidate

        # 方式 b：用户输入归一化后匹配
        normalized_input = normalize_city_name(user_text)
        if normalized_input != user_text and candidate.name == normalized_input:
            return candidate

        # 方式 c：对数据库名称也归一化后匹配
        normalized_db_name = normalize_city_name(candidate.name)
        if normalized_db_name != candidate.name:
            if normalized_db_name in user_text:
                return candidate
            # 双向归一化匹配
            if normalized_input != user_text and normalized_input == normalized_db_name:
                return candidate

    return None


def get_normalized_display_name(candidate: CityCandidate) -> str:
    """获取候选城市的显示名称。

    如果 display_name 与 name 不同，使用 display_name；
    否则对 name 应用 normalize 以去除可能的后缀。
    """
    if candidate.display_name != candidate.name:
        return candidate.display_name
    return candidate.name


def resolve_city_from_conversation(
    current_message: str,
    recent_user_messages: list[str],
    city_candidates: list[CityCandidate],
) -> Optional[CityCandidate]:
    """解析多轮对话中的目标城市。

    优先级（从高到低）：
    1. 当前消息中明确提到的城市（最高优先级）
    2. 从最近 user 消息向最旧 user 消息倒序查找
    3. 未找到 → 返回 None（退化为 P1 模式）

    只检查 role == "user" 的消息（由调用方保证）。
    跳过 assistant 消息（调用方不应传入）。
    当前消息明确出现新城市时自动覆盖历史城市。

    Args:
        current_message: 用户当前消息文本。
        recent_user_messages: 最近的用户消息列表（时间正序，不含当前消息）。
            调用方负责只传入 role=="user" 的消息。
        city_candidates: 数据库中所有城市候选列表。

    Returns:
        解析到的城市，或 None。

    Examples:
        # 当前消息有城市 → 直接返回
        >>> candidates = [CityCandidate(name="杭州", province="浙江省", city_id=1)]
        >>> resolve_city_from_conversation("推荐杭州一日游", [], candidates)
        CityCandidate(name="杭州", ...)

        # 当前消息无城市，从历史继承
        >>> resolve_city_from_conversation("天气怎么样", ["推荐杭州一日游"], candidates)
        CityCandidate(name="杭州", ...)

        # 新城市覆盖旧城市
        >>> resolve_city_from_conversation("成都呢", ["推荐杭州一日游"], candidates)
        CityCandidate(name="成都", ...)

        # 历史无城市
        >>> resolve_city_from_conversation("你好", ["今天天气不错"], candidates)
        None
    """
    if not city_candidates:
        return None

    # 1. 优先当前消息
    result = find_mentioned_city(current_message, city_candidates)
    if result is not None:
        return result

    # 2. 倒序查找历史 user 消息（最近优先）
    for msg_text in reversed(recent_user_messages):
        if not msg_text or not msg_text.strip():
            continue
        result = find_mentioned_city(msg_text, city_candidates)
        if result is not None:
            return result

    return None


def resolve_weather_city_name(candidate: CityCandidate) -> str:
    """获取适合天气 API 查询的城市名称。

    对"北京城区"、"上海城区"等内部名称进行归一化，
    确保天气查询和 Prompt 中使用用户友好的城市名。

    Examples:
        >>> resolve_weather_city_name(CityCandidate("北京城区", "北京市", 1))
        '北京'
        >>> resolve_weather_city_name(CityCandidate("杭州", "浙江省", 2))
        '杭州'
    """
    normalized = normalize_city_name(candidate.name)
    return normalized if normalized else candidate.name
