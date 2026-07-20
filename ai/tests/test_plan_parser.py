"""JSON 解析器单元测试"""
import pytest
from xingzhi_ai.plan_parser import extract_and_parse_json, PlanParseError


class TestExtractAndParseJson:
    def test_pure_json_object(self):
        result = extract_and_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_whitespace(self):
        result = extract_and_parse_json('  \n  {"key": "value"}  \n  ')
        assert result == {"key": "value"}

    def test_json_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        result = extract_and_parse_json(raw)
        assert result == {"key": "value"}

    def test_plain_fence(self):
        raw = '```\n{"key": "value"}\n```'
        result = extract_and_parse_json(raw)
        assert result == {"key": "value"}

    def test_text_before_json(self):
        raw = 'Here is your plan:\n{"title": "test", "days": 3}'
        result = extract_and_parse_json(raw)
        assert result == {"title": "test", "days": 3}

    def test_multiple_objects_rejected(self):
        raw = '```json\n{"a": 1}\n```\n```json\n{"b": 2}\n```'
        with pytest.raises(PlanParseError):
            extract_and_parse_json(raw)

    def test_array_toplevel_rejected(self):
        raw = '[{"a": 1}, {"b": 2}]'
        with pytest.raises(PlanParseError):
            extract_and_parse_json(raw)

    def test_invalid_json(self):
        raw = '{key: "value"}'
        with pytest.raises(PlanParseError):
            extract_and_parse_json(raw)

    def test_empty_string(self):
        with pytest.raises(PlanParseError):
            extract_and_parse_json("")

    def test_empty_object(self):
        with pytest.raises(PlanParseError):
            extract_and_parse_json("{}")

    def test_nested_json(self):
        raw = '{"outer": {"inner": [1, 2, 3]}}'
        result = extract_and_parse_json(raw)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_whitespace_only(self):
        with pytest.raises(PlanParseError):
            extract_and_parse_json("   \n  ")
