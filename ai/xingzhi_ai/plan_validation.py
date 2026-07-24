"""旅行计划业务验证 — 在 Pydantic Schema 验证之后进行资源引用校验

纯函数，不依赖数据库，可独立测试。

验证规则：
1. 资源 ID 必须在候选集合中
2. 资源 ID 与类型必须匹配（不能把景点 ID 标为 restaurant）
3. 资源 ID 与名称必须匹配
4. 目的地 ID 和名称必须与后端匹配城市一致
5. days 一致
6. 预算基本一致
7. 同日不无故重复景点
8. 提供安全标准化（覆盖名称/地址）

所有验证结果通过 ValidationResult 返回。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from xingzhi_ai.plan_schema import StructuredTravelPlan


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # 标准化后的计划（名称/地址被数据库值覆盖）
    normalized_plan: Optional[StructuredTravelPlan] = None


# 同一天内重复同一景点的最大允许次数（超过则为错误）
MAX_SAME_SCENIC_PER_DAY = 1
# 多天重复同一景点最多允许天数
MAX_SAME_SCENIC_ACROSS_DAYS = 2


def validate_plan_resources(
    plan: StructuredTravelPlan,
    *,
    matched_city_id: int,
    matched_city_name: str,
    matched_province: str,
    requested_days: int,
    scenic_candidates: dict[int, dict],
    hotel_candidates: dict[int, dict],
    restaurant_candidates: dict[int, dict],
    entertainment_candidates: dict[int, dict] | None = None,
    mall_candidates: dict[int, dict] | None = None,
) -> ValidationResult:
    """验证旅行计划中的资源引用。

    在 Pydantic Schema 验证通过后调用，进行业务层面的资源引用校验。

    Args:
        plan: Pydantic 验证后的结构化计划。
        matched_city_id: 后端匹配的城市 ID。
        matched_city_name: 后端匹配的城市名称。
        matched_province: 城市所在省份。
        requested_days: 用户请求的天数。
        scenic_candidates: {resource_id: {name, address, ...}} 候选景点映射。
        hotel_candidates: {resource_id: {name, address, ...}} 候选酒店映射。
        restaurant_candidates: {resource_id: {name, address, ...}} 候选餐厅映射。

    Returns:
        ValidationResult: 包含验证结果和标准化后的计划。
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. 目的地校验
    if plan.destination.city_id != matched_city_id:
        errors.append(
            f"目的地 ID 不匹配: 期望 {matched_city_id}，实际 {plan.destination.city_id}"
        )
    if plan.destination.name != matched_city_name:
        errors.append(
            f"目的地名称不匹配: 期望 {matched_city_name}，实际 {plan.destination.name}"
        )

    # 2. 天数校验
    if plan.days != requested_days:
        errors.append(f"天数不匹配: 期望 {requested_days}，实际 {plan.days}")

    # 如果有致命错误，直接返回
    if errors:
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    # 3. 逐日验证资源引用
    all_scenic_ids_used: list[tuple[int, int]] = []  # (day, resource_id)

    for day_plan in plan.itinerary:
        day_num = day_plan.day

        # 3a. 验证行程项目
        for item in day_plan.items:
            rt = item.resource_type
            rid = item.resource_id

            if rt == "general_activity":
                # 一般活动不需要 resource_id
                if rid is not None:
                    warnings.append(f"Day {day_num}: general_activity 不应有 resource_id")
                continue

            if rid is None:
                errors.append(f"Day {day_num}: {rt} '{item.name}' 缺少 resource_id")
                continue

            # 验证 ID 存在且类型匹配
            if rt == "scenic_spot":
                if rid not in scenic_candidates:
                    errors.append(f"Day {day_num}: 景点 ID {rid} ('{item.name}') 不在候选列表中")
                else:
                    _normalize_item(item, scenic_candidates[rid])
                    all_scenic_ids_used.append((day_num, rid))

            elif rt == "restaurant":
                if rid not in restaurant_candidates:
                    errors.append(f"Day {day_num}: 餐厅 ID {rid} ('{item.name}') 不在候选列表中")
                else:
                    _normalize_item(item, restaurant_candidates[rid])

            elif rt == "hotel":
                if rid not in hotel_candidates:
                    errors.append(f"Day {day_num}: 酒店 ID {rid} ('{item.name}') 不在候选列表中")
                else:
                    _normalize_item(item, hotel_candidates[rid])

            # 验证 resource_id 与 name 匹配
            if rid and not errors:
                candidate = _get_candidate(rt, rid, scenic_candidates, hotel_candidates, restaurant_candidates, entertainment_candidates, mall_candidates)
                if candidate and item.name != candidate.get("name", ""):
                    warnings.append(
                        f"Day {day_num}: 名称标准化 '{item.name}' → '{candidate['name']}'"
                    )

        # 3b. 验证餐厅
        for meal in day_plan.meals:
            if meal.resource_id:
                if meal.resource_id not in restaurant_candidates:
                    errors.append(
                        f"Day {day_num}: 用餐餐厅 ID {meal.resource_id} ('{meal.name}') 不在候选列表中"
                    )
                elif meal.name != restaurant_candidates[meal.resource_id].get("name", ""):
                    warnings.append(
                        f"Day {day_num}: 餐厅名称标准化 '{meal.name}' → "
                        f"'{restaurant_candidates[meal.resource_id]['name']}'"
                    )

        # 3c. 验证酒店
        if day_plan.hotel and day_plan.hotel.resource_id:
            hid = day_plan.hotel.resource_id
            if hid not in hotel_candidates:
                errors.append(f"Day {day_num}: 酒店 ID {hid} ('{day_plan.hotel.name}') 不在候选列表中")
            elif day_plan.hotel.name != hotel_candidates[hid].get("name", ""):
                warnings.append(
                    f"Day {day_num}: 酒店名称标准化 '{day_plan.hotel.name}' → "
                    f"'{hotel_candidates[hid]['name']}'"
                )

    # 4. 同日重复景点检查
    day_scenic_map: dict[int, set[int]] = {}
    for day_num, rid in all_scenic_ids_used:
        day_scenic_map.setdefault(day_num, set()).add(rid)

    for day_num, scenic_set in day_scenic_map.items():
        # 统计同一天内每个景点的出现次数
        day_items = [(d, r) for d, r in all_scenic_ids_used if d == day_num]
        scenic_counts: dict[int, int] = {}
        for _, rid in day_items:
            scenic_counts[rid] = scenic_counts.get(rid, 0) + 1
        for rid, count in scenic_counts.items():
            if count > MAX_SAME_SCENIC_PER_DAY:
                errors.append(f"Day {day_num}: 景点 ID {rid} 在同一天重复出现 {count} 次")

    # 5. 跨天重复检查
    scenic_day_count: dict[int, int] = {}
    for day_num, rid in all_scenic_ids_used:
        if rid not in scenic_day_count:
            scenic_day_count[rid] = len({d for d, r in all_scenic_ids_used if r == rid})
    for rid, day_count in scenic_day_count.items():
        if day_count > MAX_SAME_SCENIC_ACROSS_DAYS:
            warnings.append(
                f"景点 ID {rid} 在 {day_count} 天中重复出现，请确认是否有合理理由"
            )

    # 6. 预算基本一致性检查
    if plan.budget.estimated_total > 0:
        breakdown_total = sum([
            plan.budget.breakdown.tickets,
            plan.budget.breakdown.food,
            plan.budget.breakdown.lodging,
            plan.budget.breakdown.transport,
            plan.budget.breakdown.other,
        ])
        if breakdown_total > 0:
            diff_ratio = abs(plan.budget.estimated_total - breakdown_total) / max(
                plan.budget.estimated_total, breakdown_total
            )
            if diff_ratio > 0.3:  # 差异超过 30% 警告
                warnings.append(
                    f"预估总费用 ({plan.budget.estimated_total:.0f}) 与 "
                    f"明细合计 ({breakdown_total:.0f}) 差异较大"
                )

        # 超预算检查
        if plan.budget.requested_total and plan.budget.estimated_total > plan.budget.requested_total * 1.2:
            # 检查是否在 assumptions 中说明
            over_budget_explained = any(
                "预算" in a or "费用" in a or "超" in a
                for a in plan.assumptions
            )
            if not over_budget_explained:
                warnings.append(
                    f"预估总费用 ({plan.budget.estimated_total:.0f}) "
                    f"超出请求预算 ({plan.budget.requested_total:.0f})，但未在 assumptions 中说明"
                )

    # 构建验证结果
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        normalized_plan=plan if not errors else None,
    )


def _get_candidate(
    resource_type: str,
    resource_id: int,
    scenics: dict[int, dict],
    hotels: dict[int, dict],
    restaurants: dict[int, dict],
    entertainments: dict[int, dict] | None = None,
    malls: dict[int, dict] | None = None,
) -> Optional[dict]:
    """获取候选资源"""
    if resource_type == "scenic_spot":
        return scenics.get(resource_id)
    elif resource_type == "hotel":
        return hotels.get(resource_id)
    elif resource_type == "restaurant":
        return restaurants.get(resource_id)
    elif resource_type == "entertainment":
        return entertainments.get(resource_id) if entertainments else None
    elif resource_type == "shopping_mall":
        return malls.get(resource_id) if malls else None
    return None


def _normalize_item(item, candidate: dict) -> None:
    """用数据库中的标准名称和地址覆盖模型输出。

    这是安全的确定性标准化，不改 resource_id。
    """
    if "name" in candidate:
        item.name = candidate["name"]
    if "address" in candidate:
        item.address = candidate.get("address") or item.address
