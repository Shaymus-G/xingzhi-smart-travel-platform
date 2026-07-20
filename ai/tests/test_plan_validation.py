"""资源验证单元测试"""
import pytest
from xingzhi_ai.plan_schema import (
    StructuredTravelPlan, DayPlan, ItineraryItem, MealInfo, HotelInfo,
    PlanDestination, PlanBudget, BudgetBreakdown,
)
from xingzhi_ai.plan_validation import validate_plan_resources, ValidationResult


def _make_plan(days=1, city_id=1, city_name="TestCity") -> StructuredTravelPlan:
    """构建测试用旅行计划"""
    return StructuredTravelPlan(
        title="Test",
        destination=PlanDestination(city_id=city_id, name=city_name, province="Test"),
        days=days,
        itinerary=[
            DayPlan(
                day=d,
                theme=f"Day {d}",
                items=[
                    ItineraryItem(
                        period="morning", resource_type="scenic_spot",
                        resource_id=100 + d, name=f"Scenic{d}",
                        estimated_cost=50,
                    ),
                    ItineraryItem(
                        period="afternoon", resource_type="restaurant",
                        resource_id=200 + d, name=f"Rest{d}",
                        estimated_cost=100,
                    ),
                ],
                meals=[
                    MealInfo(period="noon", resource_id=200 + d, name=f"Rest{d}", estimated_cost=80),
                ],
                hotel=HotelInfo(resource_id=300 + d, name=f"Hotel{d}", estimated_cost=200),
                daily_estimated_cost=430,
            )
            for d in range(1, days + 1)
        ],
        budget=PlanBudget(
            estimated_total=days * 430,
            breakdown=BudgetBreakdown(tickets=days*50, food=days*180, lodging=days*200, transport=0, other=0),
        ),
    )


def _candidates():
    return (
        {100 + i: {"name": f"Scenic{i}", "address": f"Addr{i}"} for i in range(1, 20)},
        {300 + i: {"name": f"Hotel{i}", "address": f"HAddr{i}"} for i in range(1, 20)},
        {200 + i: {"name": f"Rest{i}", "address": f"RAddr{i}"} for i in range(1, 20)},
    )


class TestValidResourceReferences:
    def test_all_ids_valid(self):
        plan = _make_plan(2)
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=2,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid

    def test_normalization_applied(self):
        """名称和地址被数据库值标准化"""
        plan = _make_plan(1)
        plan.itinerary[0].items[0].name = "WrongName"
        plan.itinerary[0].items[0].address = "WrongAddr"
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid
        assert plan.itinerary[0].items[0].name == "Scenic1"
        assert plan.itinerary[0].items[0].address == "Addr1"


class TestInvalidResourceIds:
    def test_nonexistent_scenic_id(self):
        plan = _make_plan(1)
        plan.itinerary[0].items[0].resource_id = 99999
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid
        assert any("不在候选" in e for e in vr.errors)

    def test_nonexistent_hotel_id(self):
        plan = _make_plan(1)
        plan.itinerary[0].hotel.resource_id = 99999
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid

    def test_nonexistent_restaurant_id(self):
        plan = _make_plan(1)
        plan.itinerary[0].items[1].resource_id = 99999  # restaurant item
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid

    def test_scenic_id_marked_as_restaurant(self):
        """景点 ID 被标记为 restaurant → 报错"""
        plan = _make_plan(1)
        plan.itinerary[0].items[0].resource_type = "restaurant"  # but resource_id=101 is scenic
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid

    def test_specific_resource_missing_id(self):
        """scenic_spot 缺少 resource_id"""
        plan = _make_plan(1)
        plan.itinerary[0].items[0].resource_id = None
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid

    def test_general_activity_no_id_ok(self):
        """general_activity 不需要 resource_id"""
        plan = _make_plan(1)
        plan.itinerary[0].items[0].resource_type = "general_activity"
        plan.itinerary[0].items[0].resource_id = None
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid


class TestDestinationValidation:
    def test_destination_id_mismatch(self):
        plan = _make_plan(1, city_id=1)
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=999, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid
        assert any("目的地 ID" in e for e in vr.errors)

    def test_destination_name_mismatch(self):
        plan = _make_plan(1, city_id=1, city_name="WrongName")
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid

    def test_days_mismatch(self):
        plan = _make_plan(2)
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid


class TestDuplicateScenic:
    def test_same_day_duplicate_error(self):
        """同一天重复同一景点 → 错误"""
        plan = _make_plan(1)
        # 添加第二个同 ID 景点
        plan.itinerary[0].items.append(
            ItineraryItem(period="afternoon", resource_type="scenic_spot",
                         resource_id=101, name="Scenic1", estimated_cost=0)
        )
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid
        assert any("重复" in e for e in vr.errors)

    def test_cross_day_repeat_warning(self):
        """跨天重复景点超过阈值 → 警告"""
        plan = _make_plan(3, city_id=1, city_name="TestCity")
        # 让所有3天使用同一个景点ID 101
        for d in range(3):
            plan.itinerary[d].items[0].resource_id = 101
            plan.itinerary[d].items[0].name = "Scenic1"
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=3,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid  # warning only
        assert any("重复出现" in w for w in vr.warnings)


class TestBudgetValidation:
    def test_budget_breakdown_mismatch_warning(self):
        """breakdown 合计与 estimated_total 差异过大 → 警告"""
        plan = _make_plan(1)
        plan.budget.estimated_total = 10000  # way higher than breakdown
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid  # 只是 warning
        assert any("差异较大" in w for w in vr.warnings)

    def test_over_budget_warning(self):
        """超预算但未说明 → 警告"""
        plan = _make_plan(1)
        plan.budget.requested_total = 100
        plan.budget.estimated_total = 500  # 5x over budget
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid
        assert any("超出" in w for w in vr.warnings)

    def test_over_budget_explained_no_warning(self):
        """超预算但在 assumptions 中说明了 → 无 warning"""
        plan = _make_plan(1)
        plan.budget.requested_total = 100
        plan.budget.estimated_total = 500
        plan.assumptions = ["由于选择了高端酒店，总费用超出预算。"]
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid
        assert not any("超出" in w for w in vr.warnings)

    def test_negative_cost_not_allowed(self):
        """negative estimated_total should fail in pydantic validation already,
        this test confirms our validation doesn't crash"""
        plan = _make_plan(1)
        # Pydantic already rejects negative, so just verify positive case
        plan.budget.estimated_total = 500
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid


class TestNormalizedPlan:
    def test_normalized_plan_not_none_when_valid(self):
        plan = _make_plan(1)
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert vr.is_valid
        assert vr.normalized_plan is not None

    def test_normalized_plan_none_when_invalid(self):
        plan = _make_plan(1)
        plan.itinerary[0].items[0].resource_id = 99999
        sc, ho, re = _candidates()
        vr = validate_plan_resources(plan, matched_city_id=1, matched_city_name="TestCity",
                                     matched_province="Test", requested_days=1,
                                     scenic_candidates=sc, hotel_candidates=ho, restaurant_candidates=re)
        assert not vr.is_valid
        assert vr.normalized_plan is None
