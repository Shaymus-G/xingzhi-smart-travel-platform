"""上下文管理 — 消息过滤、裁剪、组装

纯函数，不依赖数据库或外部服务，可独立测试。

P2 新增：旅游上下文注入。
"""

from xingzhi_ai.types import ChatMessage
from xingzhi_ai.prompts import build_system_prompt

# 默认上限
DEFAULT_MAX_MESSAGES = 20
DEFAULT_MAX_CHARS = 8000

# 合法的聊天消息 role
_VALID_ROLES = frozenset({"user", "assistant", "system"})


def filter_valid_messages(
    messages: list[ChatMessage],
    *,
    exclude_empty: bool = True,
) -> list[ChatMessage]:
    """过滤消息列表：仅保留合法 role，可选去除空 content。

    Args:
        messages: 原始消息列表。
        exclude_empty: 是否剔除 content 为空（去除空白后）的消息。

    Returns:
        过滤后的消息列表（保持原有顺序）。
    """
    result: list[ChatMessage] = []
    for msg in messages:
        role = msg.get("role")
        if role not in _VALID_ROLES:
            continue
        if exclude_empty:
            content = msg.get("content", "")
            if not content.strip():
                continue
        result.append(msg)
    return result


def trim_context(
    messages: list[ChatMessage],
    *,
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
    preserve_latest_user: bool = True,
) -> list[ChatMessage]:
    """按数量和字符数裁剪上下文消息。

    裁剪策略：
    1. 从旧到新累积，超出限制时从最旧消息开始丢弃。
    2. system 消息不参与裁剪计数，始终保留。
    3. 可选保留最新一条 user 消息（确保用户问题不丢失）。

    注意：当 preserve_latest_user=True 且无需裁剪时，消息顺序不变。
    仅当最新 user 消息会被裁剪掉时，才将其移到末尾并强制保留。

    Args:
        messages: 已过滤并按时间正序排列的消息列表。
        max_messages: 最大非 system 消息数量。
        max_chars: 非 system 消息最大总字符数。
        preserve_latest_user: 是否始终保留最后一条 user 消息。

    Returns:
        裁剪后的消息列表（保持原有顺序）。
    """
    # 分离 system 消息和其他消息
    system_msgs: list[ChatMessage] = []
    other_msgs: list[ChatMessage] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_msgs.append(msg)
        else:
            other_msgs.append(msg)

    # 第一步：正常裁剪（不特殊处理任何消息）
    kept: list[ChatMessage] = []
    total_chars = 0

    for msg in other_msgs:
        msg_len = len(msg.get("content", ""))
        while kept and (
            len(kept) + 1 > max_messages
            or total_chars + msg_len > max_chars
        ):
            dropped = kept.pop(0)
            total_chars -= len(dropped.get("content", ""))
        kept.append(msg)
        total_chars += msg_len

    # 第二步：如果启用 preserve_latest_user，检查最新 user 消息是否已被裁剪
    if preserve_latest_user and other_msgs:
        # 找到原始列表中的最新 user 消息
        latest_user: ChatMessage | None = None
        for i in range(len(other_msgs) - 1, -1, -1):
            if other_msgs[i].get("role") == "user":
                latest_user = other_msgs[i]
                break

        if latest_user is not None:
            # 检查该消息是否在 kept 中（通过 content 和 role 匹配）
            # 由于消息没有唯一 ID，使用内容匹配
            in_kept = any(
                m.get("role") == latest_user["role"]
                and m.get("content") == latest_user["content"]
                for m in kept
            )

            if not in_kept:
                # 最新 user 消息被裁剪了，需要强制加回
                latest_len = len(latest_user.get("content", ""))
                while kept and (
                    len(kept) + 1 > max_messages
                    or total_chars + latest_len > max_chars
                ):
                    dropped = kept.pop(0)
                    total_chars -= len(dropped.get("content", ""))
                kept.append(latest_user)
                total_chars += latest_len

    return system_msgs + kept


def build_messages_with_system_prompt(
    history: list[ChatMessage],
    current_message: ChatMessage,
    *,
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
    with_grounding: bool = False,
) -> list[ChatMessage]:
    """完整的上下文构建流程。

    步骤：
        1. 过滤历史消息
        2. 裁剪上下文
        3. 添加 system prompt（可选 grounding 规则）
        4. 添加当前消息（确保不重复）

    Args:
        history: 数据库中的历史消息列表（按时间正序）。
        current_message: 用户当前消息。
        max_messages: 最大非 system 消息数。
        max_chars: 最大非 system 字符数。
        with_grounding: 是否附加 Grounding 安全规则（P2）。

    Returns:
        完整的 messages 列表，可直接传给 DeepSeek API。
    """
    # 1. 过滤
    filtered = filter_valid_messages(history)

    # 2. 裁剪
    trimmed = trim_context(
        filtered,
        max_messages=max_messages,
        max_chars=max_chars,
        preserve_latest_user=True,
    )

    # 3. 构建最终消息列表
    result: list[ChatMessage] = []

    # 添加 system prompt（如果还没有）
    system_prompt = build_system_prompt(with_grounding=with_grounding)
    has_system = any(msg.get("role") == "system" for msg in trimmed)
    if not has_system:
        result.append(ChatMessage(role="system", content=system_prompt))

    # 添加裁剪后的历史
    result.extend(trimmed)

    # 4. 添加当前消息（避免重复：检查是否已有内容相同的 user 消息）
    current_content = current_message.get("content", "").strip()
    is_duplicate = any(
        m.get("role") == "user"
        and m.get("content", "").strip() == current_content
        for m in result
    )

    if not is_duplicate:
        result.append(current_message)

    return result


def build_messages_with_travel_context(
    history: list[ChatMessage],
    current_message: ChatMessage,
    travel_context_block: str,
    *,
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[ChatMessage]:
    """P2 增强上下文构建：包含旅游数据块和 Grounding 规则。

    与 build_messages_with_system_prompt 的区别：
    - 系统提示词会附加 Grounding 安全规则
    - 系统提示词中不嵌入旅游数据块（数据块作为独立 system message）
    - 保持历史消息和当前消息的裁剪逻辑不变

    消息结构：
        [0] system: 基础系统提示词 + Grounding 规则
        [1] system: 旅游数据块（如果非空）
        [2..N-1] 裁剪后的历史消息
        [N] 当前用户消息

    Args:
        history: 数据库中的历史消息列表（按时间正序）。
        current_message: 用户当前消息。
        travel_context_block: 构建好的旅游数据文本块（可能为空）。
        max_messages: 最大非 system 消息数。
        max_chars: 最大非 system 字符数。

    Returns:
        完整的 messages 列表，可直接传给 DeepSeek API。
    """
    # 1. 过滤
    filtered = filter_valid_messages(history)

    # 2. 裁剪
    trimmed = trim_context(
        filtered,
        max_messages=max_messages,
        max_chars=max_chars,
        preserve_latest_user=True,
    )

    # 3. 构建最终消息列表
    result: list[ChatMessage] = []

    # 3a. 主 system prompt（含 Grounding 规则）
    system_prompt = build_system_prompt(with_grounding=True)
    has_system = any(msg.get("role") == "system" for msg in trimmed)
    if not has_system:
        result.append(ChatMessage(role="system", content=system_prompt))

    # 3b. 旅游数据块作为独立 system message（不伪装成用户消息）
    if travel_context_block.strip():
        result.append(ChatMessage(role="system", content=travel_context_block.strip()))

    # 添加裁剪后的历史
    result.extend(trimmed)

    # 4. 添加当前消息
    current_content = current_message.get("content", "").strip()
    is_duplicate = any(
        m.get("role") == "user"
        and m.get("content", "").strip() == current_content
        for m in result
    )

    if not is_duplicate:
        result.append(current_message)

    return result
