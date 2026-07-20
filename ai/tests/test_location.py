"""城市识别单元测试 — 纯函数，不依赖数据库"""
import pytest
from xingzhi_ai.location import (
    CityCandidate,
    normalize_city_name,
    find_mentioned_city,
    resolve_city_from_conversation,
    resolve_weather_city_name,
)


# ==================== normalize_city_name ====================


class TestNormalizeCityName:
    def test_strips_shi_suffix(self):
        assert normalize_city_name("杭州市") == "杭州"

    def test_strips_xian_suffix(self):
        assert normalize_city_name("长沙县") == "长沙"

    def test_strips_qu_suffix(self):
        assert normalize_city_name("北京城区") == "北京"

    def test_strips_zizhizhou_suffix(self):
        assert normalize_city_name("湘西土家族苗族自治州") == "湘西土家族苗族"

    def test_strips_diqu_suffix(self):
        assert normalize_city_name("阿里地区") == "阿里"

    def test_strips_meng_suffix(self):
        assert normalize_city_name("兴安盟") == "兴安"

    def test_preserves_bare_name(self):
        assert normalize_city_name("杭州") == "杭州"

    def test_preserves_zhou_in_name(self):
        """单字"州"是城市名本体，不应剥离（如杭州、苏州、广州）"""
        assert normalize_city_name("杭州") == "杭州"
        assert normalize_city_name("苏州") == "苏州"
        assert normalize_city_name("广州") == "广州"

    def test_handles_whitespace(self):
        assert normalize_city_name("  北京市  ") == "北京"

    def test_handles_empty(self):
        result = normalize_city_name("")
        assert result == ""


# ==================== find_mentioned_city ====================


def _make_candidates(*names_and_provinces) -> list[CityCandidate]:
    """辅助：从 (name, province) 元组列表构建候选"""
    return [
        CityCandidate(name=name, province=province, city_id=i + 1)
        for i, (name, province) in enumerate(names_and_provinces)
    ]


class TestFindMentionedCity:
    def test_exact_match(self):
        candidates = _make_candidates(
            ("杭州", "浙江省"),
            ("苏州", "江苏省"),
            ("南京", "江苏省"),
        )
        result = find_mentioned_city("我想去杭州旅游", candidates)
        assert result is not None
        assert result.name == "杭州"

    def test_user_with_shi_suffix(self):
        """用户说"杭州市"，数据库是"杭州" """
        candidates = _make_candidates(("杭州", "浙江省"))
        result = find_mentioned_city("推荐杭州市一日游", candidates)
        assert result is not None
        assert result.name == "杭州"

    def test_db_with_qu_suffix(self):
        """用户说"北京"，数据库是"北京城区" """
        candidates = _make_candidates(("北京城区", "北京市"))
        result = find_mentioned_city("我想去北京", candidates)
        assert result is not None
        assert result.name == "北京城区"

    def test_both_normalized(self):
        """用户说"北京市"，数据库是"北京城区" """
        candidates = _make_candidates(("北京城区", "北京市"))
        result = find_mentioned_city("北京市三日游推荐", candidates)
        assert result is not None
        assert result.name == "北京城区"

    def test_longest_match_first(self):
        """最长名称优先，避免"江"匹配到"江门" """
        candidates = _make_candidates(
            ("江门", "广东省"),
            ("江", "某省"),
        )
        # 按名称长度降序排列，"江门"(2) 在 "江"(1) 之前
        result = find_mentioned_city("江门有什么好玩的", candidates)
        assert result is not None
        assert result.name == "江门"

    def test_no_city_found(self):
        candidates = _make_candidates(("杭州", "浙江省"))
        result = find_mentioned_city("今天天气真好", candidates)
        assert result is None

    def test_empty_text(self):
        candidates = _make_candidates(("杭州", "浙江省"))
        assert find_mentioned_city("", candidates) is None

    def test_empty_candidates(self):
        assert find_mentioned_city("去杭州", []) is None

    def test_multiple_cities_first_wins(self):
        """多城市时返回文本中最先出现的（也是最长优先的）"""
        candidates = _make_candidates(
            ("杭州", "浙江省"),
            ("南京", "江苏省"),
            ("西安", "陕西省"),
        )
        result = find_mentioned_city("从杭州出发经过南京到西安的路线", candidates)
        assert result is not None
        # "西安"最长（2个字），但"杭州"和"南京"也是2个字
        # 长度相同时按原始 candidates 排序后的顺序
        # "西安"排在候选最后，但它最长优先时会排在前面
        # 实际上三者长度相同，排序后原顺序不定（sorted 稳定）
        # 应该匹配第一个出现在文本中的候选
        assert result.name == "杭州"

    def test_no_false_match_short_word(self):
        """不把普通短词误匹配为城市"""
        candidates = _make_candidates(
            ("江门", "广东省"),
            ("杭州", "浙江省"),
        )
        result = find_mentioned_city("长江大桥怎么走", candidates)
        # "江"会尝试匹配"江门"？不，精确子串匹配 "江门" in "长江大桥怎么走" → False
        assert result is None

    def test_partial_name_match(self):
        """子串匹配：用户说"杭州"匹配候选"杭州" """
        candidates = _make_candidates(("杭州", "浙江省"))
        result = find_mentioned_city("杭州西湖", candidates)
        assert result is not None
        assert result.name == "杭州"

    def test_city_in_middle_of_text(self):
        candidates = _make_candidates(("成都", "四川省"))
        result = find_mentioned_city("帮我规划一个成都三日游", candidates)
        assert result is not None
        assert result.name == "成都"


# ==================== resolve_city_from_conversation ====================


def _make_city_list(*names_and_provinces) -> list[CityCandidate]:
    """辅助：从 (name, province) 元组列表构建候选"""
    return [
        CityCandidate(name=name, province=province, city_id=i + 1)
        for i, (name, province) in enumerate(names_and_provinces)
    ]


class TestResolveCityFromConversation:
    def test_current_message_has_priority(self):
        """当前消息明确包含杭州"""
        candidates = _make_city_list(("杭州", "浙江省"), ("成都", "四川省"))
        result = resolve_city_from_conversation(
            "推荐杭州一日游", [], candidates
        )
        assert result is not None
        assert result.name == "杭州"

    def test_fallback_to_previous_user_message(self):
        """当前消息无城市，上一条 user 消息包含杭州"""
        candidates = _make_city_list(("杭州", "浙江省"))
        result = resolve_city_from_conversation(
            "如果天气不好怎么调整",
            ["推荐杭州一日游方案"],
            candidates,
        )
        assert result is not None
        assert result.name == "杭州"

    def test_skip_assistant_not_in_user_list(self):
        """调用方只传入 user 消息，assistant 消息不参与匹配"""
        candidates = _make_city_list(("杭州", "浙江省"), ("上海城区", "上海市"))
        # 调用方只传入 user 消息列表（不含 assistant）
        result = resolve_city_from_conversation(
            "天气怎么样",
            ["我想去杭州玩"],  # 只有 user 消息
            candidates,
        )
        assert result is not None
        assert result.name == "杭州"

    def test_new_city_overrides_history(self):
        """当前消息明确提到成都，历史为杭州 → 选择成都"""
        candidates = _make_city_list(
            ("杭州", "浙江省"), ("成都", "四川省")
        )
        result = resolve_city_from_conversation(
            "成都呢，有什么好玩的",
            ["推荐杭州一日游方案"],
            candidates,
        )
        assert result is not None
        assert result.name == "成都"

    def test_most_recent_user_message_wins(self):
        """多条 user 消息分别含杭州和苏州 → 选择最近一次的苏州"""
        candidates = _make_city_list(
            ("杭州", "浙江省"), ("苏州", "江苏省")
        )
        result = resolve_city_from_conversation(
            "继续",
            ["推荐杭州一日游", "苏州有什么好玩的"],  # 苏州更近
            candidates,
        )
        assert result is not None
        assert result.name == "苏州"

    def test_no_city_in_history_returns_none(self):
        """历史和当前都无城市 → None"""
        candidates = _make_city_list(("杭州", "浙江省"))
        result = resolve_city_from_conversation(
            "你好",
            ["今天天气不错", "有什么推荐的"],
            candidates,
        )
        assert result is None

    def test_empty_history(self):
        """空历史，当前无城市 → None"""
        candidates = _make_city_list(("杭州", "浙江省"))
        result = resolve_city_from_conversation("你好", [], candidates)
        assert result is None

    def test_empty_candidates(self):
        """空候选列表 → None"""
        result = resolve_city_from_conversation(
            "去杭州", ["推荐旅游"], []
        )
        assert result is None

    def test_empty_user_messages_skipped(self):
        """空白历史消息被跳过"""
        candidates = _make_city_list(("杭州", "浙江省"))
        result = resolve_city_from_conversation(
            "继续",
            ["", "  ", "推荐杭州一日游"],
            candidates,
        )
        assert result is not None
        assert result.name == "杭州"

    def test_city_in_first_of_many_history_messages(self):
        """城市在较早的历史消息中"""
        candidates = _make_city_list(("杭州", "浙江省"))
        result = resolve_city_from_conversation(
            "还有呢",
            ["推荐杭州一日游", "西湖怎么样", "灵隐寺呢", "继续"],
            candidates,
        )
        assert result is not None
        assert result.name == "杭州"


# ==================== resolve_weather_city_name ====================


class TestResolveWeatherCityName:
    def test_chengqu_city_normalized(self):
        """北京城区 → 北京"""
        candidate = CityCandidate("北京城区", "北京市", 1)
        assert resolve_weather_city_name(candidate) == "北京"

    def test_shanghai_chengqu_normalized(self):
        """上海城区 → 上海"""
        candidate = CityCandidate("上海城区", "上海市", 2)
        assert resolve_weather_city_name(candidate) == "上海"

    def test_normal_city_unchanged(self):
        """杭州 → 杭州"""
        candidate = CityCandidate("杭州", "浙江省", 3)
        assert resolve_weather_city_name(candidate) == "杭州"

    def test_xian_city_unchanged(self):
        """长沙县 → 长沙"""
        candidate = CityCandidate("长沙县", "湖南省", 4)
        assert resolve_weather_city_name(candidate) == "长沙"

    def test_zizhizhou_city_normalized(self):
        """自治州 → 去除后缀"""
        candidate = CityCandidate("湘西土家族苗族自治州", "湖南省", 5)
        assert resolve_weather_city_name(candidate) == "湘西土家族苗族"


# ==================== 城区城市完整匹配验证 ====================


class TestChengquCityMatching:
    """验证"北京"、"北京市"、"北京城区"都能匹配到对应数据库城市"""

    def test_beijing_bare_name(self):
        """用户说"北京"匹配到"北京城区" """
        candidates = _make_city_list(("北京城区", "北京市"))
        result = find_mentioned_city("我想去北京", candidates)
        assert result is not None
        assert result.name == "北京城区"

    def test_beijing_with_shi_suffix(self):
        """用户说"北京市"匹配到"北京城区" """
        candidates = _make_city_list(("北京城区", "北京市"))
        result = find_mentioned_city("北京市三日游推荐", candidates)
        assert result is not None
        assert result.name == "北京城区"

    def test_beijing_chengqu_exact(self):
        """用户说"北京城区"精确匹配"""
        candidates = _make_city_list(("北京城区", "北京市"))
        result = find_mentioned_city("北京城区有什么好玩的", candidates)
        assert result is not None
        assert result.name == "北京城区"

    def test_shanghai_bare_name(self):
        """用户说"上海"匹配到"上海城区" """
        candidates = _make_city_list(("上海城区", "上海市"))
        result = find_mentioned_city("上海三日游", candidates)
        assert result is not None
        assert result.name == "上海城区"
