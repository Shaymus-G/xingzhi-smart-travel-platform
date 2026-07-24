"""旅行计划 Markdown 渲染器 — 确定性从验证后的 JSON 生成

纯函数，不依赖数据库或外部服务，可独立测试。

所有 Markdown 内容均来自已验证的 StructuredTravelPlan，
不重新调用模型，保证 JSON 与 Markdown 内容一致。
"""

from __future__ import annotations

from xingzhi_ai.plan_schema import StructuredTravelPlan


def _escape_md(text: str) -> str:
    """对 Markdown 特殊字符做最小安全处理。

    不改变中文文本，仅处理可能导致格式错误的字符。
    """
    if not text:
        return ""
    # 不对 # * - 等做全局转义，它们大多用于合法的标题和列表
    # 只移除可能导致注入的原始 HTML 标签
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text


def _none_to_na(value: str | None, default: str = "—") -> str:
    """将 None 转为占位符"""
    if value is None or not str(value).strip():
        return default
    return str(value).strip()


def _format_cost(cost: float) -> str:
    """格式化费用"""
    if cost == 0:
        return "免费"
    return f"¥{cost:.0f}"


def _format_time(start: str | None, end: str | None) -> str:
    """格式化时间范围"""
    s = start or "?"
    e = end or "?"
    return f"{s} - {e}"


_PERIOD_LABELS: dict[str, str] = {
    "morning": "上午",
    "noon": "中午",
    "afternoon": "下午",
    "evening": "傍晚",
    "night": "晚上",
}


def render_travel_plan_markdown(plan: StructuredTravelPlan) -> str:
    """从验证后的 StructuredTravelPlan 生成 Markdown 文本。

    生成的 Markdown 结构：
    # 标题
    ## 基本信息
    ## 行程概览
    ## 第 N 天：主题
    ### 上午 / 中午 / ...
    ### 午餐 / 晚餐
    ### 住宿
    ### 当日费用
    ## 预算明细
    ## 旅行贴士
    ## 假设与数据说明

    Args:
        plan: 经过 Pydantic + 业务验证的结构化旅行计划。

    Returns:
        Markdown 格式的文本。
    """
    lines: list[str] = []

    # 标题
    lines.append(f"# {_escape_md(plan.title)}")
    lines.append("")

    # 基本信息
    lines.append("## 基本信息")
    lines.append("")
    dest = plan.destination
    lines.append(f"- **目的地**：{_escape_md(dest.name)}")
    if dest.province:
        lines.append(f"- **省份**：{_escape_md(dest.province)}")
    lines.append(f"- **天数**：{plan.days} 天")
    if plan.travelers > 1:
        lines.append(f"- **人数**：{plan.travelers} 人")
    budget = plan.budget
    if budget.requested_total:
        lines.append(f"- **预算**：¥{budget.requested_total:.0f}")
    lines.append(f"- **预估总费用**：¥{budget.estimated_total:.0f}")
    lines.append("")

    if plan.summary:
        lines.append(f"> {_escape_md(plan.summary)}")
        lines.append("")

    # 行程概览
    lines.append("## 行程概览")
    lines.append("")
    for day_plan in plan.itinerary:
        theme = _escape_md(day_plan.theme) if day_plan.theme else f"第 {day_plan.day} 天"
        lines.append(f"- **第 {day_plan.day} 天**：{theme}")
    lines.append("")

    # 每日详情
    for day_plan in plan.itinerary:
        day_title = f"第 {day_plan.day} 天"
        if day_plan.theme:
            day_title += f"：{_escape_md(day_plan.theme)}"
        lines.append(f"## {day_title}")
        lines.append("")

        if day_plan.summary:
            lines.append(f"{_escape_md(day_plan.summary)}")
            lines.append("")

        if day_plan.weather_note:
            lines.append(f"> 🌤️ 天气备注：{_escape_md(day_plan.weather_note)}")
            lines.append("")

        # 按时段分组
        items_by_period: dict[str, list] = {}
        for item in day_plan.items:
            items_by_period.setdefault(item.period, []).append(item)

        period_order = ["morning", "noon", "afternoon", "evening", "night"]
        for period in period_order:
            if period not in items_by_period:
                continue
            label = _PERIOD_LABELS.get(period, period)
            lines.append(f"### {label}")
            lines.append("")

            for item in items_by_period[period]:
                rt_label = _resource_type_label(item.resource_type)
                lines.append(f"**{_escape_md(item.name)}** ({rt_label})")
                lines.append("")
                if item.start_time or item.end_time:
                    lines.append(f"- ⏰ 时间：{_format_time(item.start_time, item.end_time)}")
                if item.address:
                    lines.append(f"- 📍 地址：{_escape_md(item.address)}")
                if item.duration_minutes:
                    hours = item.duration_minutes // 60
                    mins = item.duration_minutes % 60
                    if hours > 0:
                        lines.append(f"- ⏱️ 预计时长：{hours} 小时 {mins} 分钟")
                    else:
                        lines.append(f"- ⏱️ 预计时长：{mins} 分钟")
                if item.estimated_cost > 0:
                    lines.append(f"- 💰 费用：{_format_cost(item.estimated_cost)}")
                elif item.resource_type != "general_activity":
                    lines.append(f"- 💰 费用：{_format_cost(item.estimated_cost)}")
                if item.reason:
                    lines.append(f"- 💡 推荐理由：{_escape_md(item.reason)}")
                if item.transport_to_next:
                    lines.append(f"- 🚗 前往下一站：{_escape_md(item.transport_to_next)}")
                lines.append("")

        # 用餐
        if day_plan.meals:
            lines.append("### 用餐")
            lines.append("")
            for meal in day_plan.meals:
                meal_label = _PERIOD_LABELS.get(meal.period, meal.period)
                lines.append(f"- **{meal_label}**：{_escape_md(meal.name)}")
                if meal.estimated_cost > 0:
                    lines.append(f"  - 预估费用：{_format_cost(meal.estimated_cost)}")
            lines.append("")

        # 住宿
        if day_plan.hotel:
            lines.append("### 住宿")
            lines.append("")
            h = day_plan.hotel
            lines.append(f"**{_escape_md(h.name)}**")
            if h.address:
                lines.append(f"- 📍 地址：{_escape_md(h.address)}")
            if h.estimated_cost > 0:
                lines.append(f"- 💰 费用：{_format_cost(h.estimated_cost)}")
            lines.append("")

        # 当日费用
        if day_plan.daily_estimated_cost > 0:
            lines.append(f"**当日预估费用**：{_format_cost(day_plan.daily_estimated_cost)}")
            lines.append("")

    # 预算明细
    lines.append("## 预算明细")
    lines.append("")
    bd = budget.breakdown
    lines.append(f"| 类别 | 金额 |")
    lines.append(f"|------|------|")
    lines.append(f"| 🎫 门票 | {_format_cost(bd.tickets)} |")
    lines.append(f"| 🍜 餐饮 | {_format_cost(bd.food)} |")
    lines.append(f"| 🏨 住宿 | {_format_cost(bd.lodging)} |")
    lines.append(f"| 🚗 交通 | {_format_cost(bd.transport)} |")
    lines.append(f"| 📦 其他 | {_format_cost(bd.other)} |")
    lines.append(f"| **合计** | **{_format_cost(budget.estimated_total)}** |")
    lines.append("")

    # 旅行贴士
    if plan.tips:
        lines.append("## 旅行贴士")
        lines.append("")
        for tip in plan.tips:
            lines.append(f"- {_escape_md(tip)}")
        lines.append("")

    # 假设与数据说明
    if plan.assumptions:
        lines.append("## 假设与数据说明")
        lines.append("")
        for assumption in plan.assumptions:
            lines.append(f"- {_escape_md(assumption)}")
        lines.append("")

    # 页脚
    lines.append("---")
    lines.append(f"*本计划由行知 AI 助手生成，{plan.days} 天行程，预估总费用 {_format_cost(budget.estimated_total)}。*")
    lines.append("*实际价格、开放时间和天气可能变化，出行前请再次确认。*")

    return "\n".join(lines)


def _resource_type_label(rt: str) -> str:
    """资源类型的中文标签"""
    labels = {
        "scenic_spot": "景点",
        "restaurant": "餐厅",
        "hotel": "酒店",
        "entertainment": "娱乐",
        "shopping_mall": "商场",
        "general_activity": "活动",
    }
    return labels.get(rt, rt)
