"""旅行计划 JSON 解析器 — 处理 DeepSeek 返回的原始文本

纯函数，不依赖数据库或外部服务。

处理场景：
- 纯 JSON 对象
- 首尾空白
- ```json ... ``` 代码围栏
- ``` ... ``` 普通围栏
- 前后有少量说明文字
- 非法 JSON / 多个对象 / 顶层非对象 → 拒绝

安全策略：
- 使用 json.JSONDecoder.raw_decode() 精确匹配括号对
- 不使用贪婪正则匹配花括号对（会跨多个对象）
- 不使用 eval / ast.literal_eval
"""

from __future__ import annotations

import json
import re
from typing import Optional


# 最大接受的模型输出长度（防止超大输出）
MAX_RESPONSE_LENGTH = 100_000


class PlanParseError(Exception):
    """计划 JSON 解析失败"""

    def __init__(self, message: str = "AI 生成的旅行计划格式无效"):
        self.message = message
        super().__init__(message)


def extract_and_parse_json(raw_response: str) -> dict:
    """从 DeepSeek 原始响应中提取并解析 JSON 对象。

    处理流程：
    1. 长度检查
    2. 去除首尾空白
    3. 尝试直接解析为 JSON
    4. 尝试提取 ```json ... ``` 代码围栏
    5. 尝试提取 ``` ... ``` 普通围栏
    6. 使用 raw_decode() 安全定位第一个完整 JSON 对象
    7. 全部失败 → PlanParseError

    Args:
        raw_response: DeepSeek 返回的原始文本。

    Returns:
        解析后的 dict。

    Raises:
        PlanParseError: 无法提取或解析 JSON 对象。
    """
    if not raw_response or not raw_response.strip():
        raise PlanParseError("AI 返回为空，无法生成旅行计划")

    text = raw_response.strip()

    # 1. 长度检查
    if len(text) > MAX_RESPONSE_LENGTH:
        raise PlanParseError("AI 返回内容过长，无法处理")

    # 2. 尝试直接解析
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            if not result:
                raise PlanParseError("AI 返回了空的 JSON 对象")
            return result
        raise PlanParseError("AI 返回的顶层结构不是 JSON 对象")
    except json.JSONDecodeError:
        pass

    # 3. 尝试提取 ```json ... ``` 围栏
    json_fence = _extract_fenced_block(text, "json")
    if json_fence is not None:
        return _parse_strict(json_fence)

    # 4. 尝试提取 ``` ... ``` 普通围栏
    plain_fence = _extract_fenced_block(text, None)
    if plain_fence is not None:
        return _parse_strict(plain_fence)

    # 5. 使用 raw_decode() 安全定位第一个完整 JSON 对象
    #    正确匹配嵌套括号，不会贪婪跨多个对象
    obj = _extract_first_json_object(text)
    if obj is not None:
        return _parse_strict(obj)

    raise PlanParseError("AI 返回中未找到有效的 JSON 对象")


def _extract_first_json_object(text: str) -> Optional[str]:
    """使用 json.JSONDecoder.raw_decode() 安全提取第一个完整 JSON 对象。

    从文本中找到第一个 '{'，然后用 raw_decode() 解析完整的嵌套对象。
    正确处理 JSON 字符串内部的 { } 和嵌套结构。
    不会贪婪跨越多個顶层对象。

    Args:
        text: 可能包含 JSON 对象的文本。

    Returns:
        第一个完整 JSON 对象的字符串，或 None。
    """
    # 找到第一个 '{'
    start_idx = text.find("{")
    if start_idx == -1:
        return None

    decoder = json.JSONDecoder()
    try:
        obj, end_idx = decoder.raw_decode(text, start_idx)
        if isinstance(obj, dict) and obj:
            return text[start_idx:end_idx]
    except json.JSONDecodeError:
        pass

    return None


def _extract_fenced_block(text: str, language: Optional[str]) -> Optional[str]:
    """提取 ```language ... ``` 围栏中的内容。

    使用非贪婪匹配 .*? 避免跨多个围栏。

    Args:
        text: 原始文本。
        language: 围栏语言标识（如 "json"），None 表示匹配任意。

    Returns:
        围栏内容，或 None。
    """
    if language:
        pattern = re.compile(rf"```{language}\s*\n(.*?)```", re.DOTALL)
    else:
        pattern = re.compile(r"```\s*\n(.*?)```", re.DOTALL)

    matches = pattern.findall(text)
    if len(matches) == 1:
        return matches[0].strip()
    return None


def _parse_strict(text: str) -> dict:
    """严格解析 JSON 文本。

    - 唯一顶层对象时才返回
    - 数组顶层 → 拒绝
    - 非法 JSON → 拒绝
    - 不使用 eval / ast.literal_eval
    """
    text = text.strip()

    # 拒绝明显的非 JSON 内容
    if text.startswith("["):
        raise PlanParseError("AI 返回的顶层结构是数组，期望 JSON 对象")

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        raise PlanParseError(f"JSON 解析失败: {str(e)[:200]}")

    if not isinstance(result, dict):
        raise PlanParseError(f"AI 返回的顶层结构不是 JSON 对象，而是 {type(result).__name__}")

    # 拒绝空对象
    if not result:
        raise PlanParseError("AI 返回了空的 JSON 对象")

    return result
