"""系统提示词管理 — 集中维护，避免散落在路由或 Service 中

P2 新增：Grounding 安全规则注入。
"""

from xingzhi_ai.travel_context import build_grounding_rules


SYSTEM_PROMPT = """
你是"行知"智慧文旅平台的 AI 旅行助手。

你需要使用中文回答用户关于：
- 城市选择；
- 景点推荐；
- 行程安排；
- 预算规划；
- 酒店和餐厅建议；
- 交通建议；
- 旅行注意事项；
- 避坑建议。

回答要求：
1. 结构清晰，分点给出建议；
2. 优先给出能够实际执行的建议；
3. 信息不足时明确说明你的假设；
4. 不编造实时天气、实时价格、实时人流或实时开放状态；
5. 没有获得平台数据时，不要声称信息来自平台数据库；
6. 对可能变化的信息提醒用户再次确认；
7. 默认使用中文回答。
""".strip()


def build_system_prompt(*, with_grounding: bool = False) -> str:
    """返回系统提示词。

    Args:
        with_grounding: 是否附加 Grounding 安全规则。
            在 P2 旅游数据增强模式下应设为 True。
    """
    if with_grounding:
        return SYSTEM_PROMPT + "\n\n" + build_grounding_rules()
    return SYSTEM_PROMPT
