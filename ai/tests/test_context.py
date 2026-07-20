"""上下文管理单元测试 — 纯函数，不依赖数据库或外部服务"""
import pytest
from xingzhi_ai.types import ChatMessage
from xingzhi_ai.context import (
    filter_valid_messages,
    trim_context,
    build_messages_with_system_prompt,
)


def make_msg(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)


# ==================== filter_valid_messages ====================


class TestFilterValidMessages:
    def test_empty_list(self):
        assert filter_valid_messages([]) == []

    def test_preserves_valid_roles(self):
        msgs = [
            make_msg("user", "hello"),
            make_msg("assistant", "hi"),
        ]
        assert filter_valid_messages(msgs) == msgs

    def test_filters_invalid_role(self):
        msgs = [
            make_msg("user", "hello"),
            make_msg("invalid_role", "bad"),
            make_msg("assistant", "hi"),
        ]
        result = filter_valid_messages(msgs)
        assert len(result) == 2
        assert all(m["role"] in ("user", "assistant") for m in result)

    def test_excludes_empty_content(self):
        msgs = [
            make_msg("user", "hello"),
            make_msg("user", "   "),
            make_msg("user", ""),
            make_msg("assistant", "hi"),
        ]
        result = filter_valid_messages(msgs)
        assert len(result) == 2

    def test_keeps_empty_content_when_exclude_empty_false(self):
        msgs = [
            make_msg("user", "hello"),
            make_msg("user", ""),
        ]
        result = filter_valid_messages(msgs, exclude_empty=False)
        assert len(result) == 2

    def test_preserves_order(self):
        msgs = [
            make_msg("user", "first"),
            make_msg("user", "   "),
            make_msg("assistant", "second"),
            make_msg("assistant", "third"),
        ]
        result = filter_valid_messages(msgs)
        contents = [m["content"] for m in result]
        assert contents == ["first", "second", "third"]

    def test_handles_none_role(self):
        msgs = [{"role": None, "content": "test"}]  # type: ignore
        result = filter_valid_messages(msgs)
        assert result == []


# ==================== trim_context ====================


class TestTrimContext:
    def test_empty_list(self):
        assert trim_context([]) == []

    def test_within_limits_returns_all(self):
        msgs = [make_msg("user", "short"), make_msg("assistant", "reply")]
        result = trim_context(msgs, max_messages=10, max_chars=1000)
        assert result == msgs

    def test_trims_by_message_count(self):
        msgs = [make_msg("user", f"msg{i}") for i in range(10)]
        result = trim_context(msgs, max_messages=5, max_chars=10000)
        # 保留最后 5 条
        assert len([m for m in result if m["role"] != "system"]) == 5
        assert result[0]["content"] == "msg5"

    def test_trims_by_char_count(self):
        msgs = [
            make_msg("user", "a" * 50),
            make_msg("assistant", "b" * 50),
            make_msg("user", "c" * 50),
        ]
        result = trim_context(msgs, max_messages=100, max_chars=90)
        # 只保留最后一条（50 < 90，但之前两条 150 > 90）
        non_system = [m for m in result if m["role"] != "system"]
        assert len(non_system) == 1
        assert non_system[0]["content"] == "c" * 50

    def test_preserves_system_message(self):
        msgs = [
            make_msg("system", "I am a helpful assistant"),
            make_msg("user", "q1"),
            make_msg("assistant", "a1"),
        ]
        result = trim_context(msgs, max_messages=10, max_chars=1000)
        system_msgs = [m for m in result if m["role"] == "system"]
        assert len(system_msgs) == 1
        assert system_msgs[0]["content"] == "I am a helpful assistant"

    def test_preserves_latest_user_message(self):
        """最新一条 user 消息不应被裁剪掉"""
        msgs = [
            make_msg("user", "q1"),
            make_msg("assistant", "a1"),
            make_msg("user", "q2"),  # 最新 user
        ]
        result = trim_context(msgs, max_messages=2, max_chars=1000)
        user_msgs = [m for m in result if m["role"] == "user"]
        assert len(user_msgs) >= 1
        assert user_msgs[-1]["content"] == "q2"

    def test_preserves_temporal_order(self):
        msgs = [
            make_msg("user", "first"),
            make_msg("assistant", "second"),
            make_msg("user", "third"),
        ]
        result = trim_context(msgs, max_messages=10, max_chars=1000)
        non_system = [m for m in result if m["role"] != "system"]
        assert non_system == msgs

    def test_no_duplicate_latest_user(self):
        """确保保留的 latest_user 不会和已有消息重复"""
        msgs = [make_msg("user", "only question")]
        result = trim_context(msgs, max_messages=10, max_chars=1000)
        user_count = sum(1 for m in result if m["role"] == "user")
        assert user_count == 1


# ==================== build_messages_with_system_prompt ====================


class TestBuildMessagesWithSystemPrompt:
    def test_adds_system_prompt(self):
        result = build_messages_with_system_prompt(
            history=[],
            current_message=make_msg("user", "hello"),
        )
        assert result[0]["role"] == "system"
        assert "行知" in result[0]["content"]

    def test_does_not_duplicate_system_prompt(self):
        result = build_messages_with_system_prompt(
            history=[make_msg("system", "existing system prompt")],
            current_message=make_msg("user", "hello"),
        )
        system_count = sum(1 for m in result if m["role"] == "system")
        assert system_count == 1

    def test_current_message_not_duplicated(self):
        """当前消息不应重复出现"""
        result = build_messages_with_system_prompt(
            history=[
                make_msg("user", "hello"),
                make_msg("assistant", "hi there"),
            ],
            current_message=make_msg("user", "hello"),  # 与历史最后一条相同
        )
        user_msgs = [m for m in result if m["role"] == "user"]
        # 当前消息与历史最后一条重复，不应添加第二次
        assert len(user_msgs) == 1

    def test_current_message_appended_when_different(self):
        result = build_messages_with_system_prompt(
            history=[make_msg("user", "old question")],
            current_message=make_msg("user", "new question"),
        )
        user_msgs = [m for m in result if m["role"] == "user"]
        assert len(user_msgs) == 2
        assert user_msgs[-1]["content"] == "new question"

    def test_with_history(self):
        history = [
            make_msg("user", "q1"),
            make_msg("assistant", "a1"),
        ]
        result = build_messages_with_system_prompt(
            history=history,
            current_message=make_msg("user", "q2"),
        )
        roles = [m["role"] for m in result]
        assert roles == ["system", "user", "assistant", "user"]

    def test_long_history_trimmed(self):
        """超长历史应该被裁剪"""
        history = [make_msg("user", f"msg{i}") for i in range(50)]
        result = build_messages_with_system_prompt(
            history=history,
            current_message=make_msg("user", "final"),
            max_messages=10,
            max_chars=5000,
        )
        non_system = [m for m in result if m["role"] != "system"]
        assert len(non_system) <= 11  # 10 history + current
        assert non_system[-1]["content"] == "final"
