"""旅行计划 Schema 验证测试"""
import pytest
from xingzhi_ai.plan_schema import StructuredTravelPlan, DayPlan, ItineraryItem, PlanDestination, PlanBudget, BudgetBreakdown


def _make_valid_plan(days=1) -> dict:
    return {
        "schema_version": "1.0",
        "title": "Test Plan",
        "destination": {"city_id": 1, "name": "Test City", "province": "Test Province"},
        "days": days,
        "travelers": 1,
        "summary": "A test plan",
        "budget": {
            "currency": "CNY",
            "requested_total": 1000,
            "estimated_total": 900,
            "breakdown": {"tickets": 100, "food": 300, "lodging": 300, "transport": 100, "other": 100},
        },
        "itinerary": [
            {
                "day": i,
                "theme": f"Day {i}",
                "summary": f"Day {i} summary",
                "items": [
                    {
                        "period": "morning",
                        "resource_type": "scenic_spot",
                        "resource_id": 1000 + i,
                        "name": f"Scenic {i}",
                        "duration_minutes": 120,
                        "estimated_cost": 50,
                    }
                ],
                "meals": [
                    {"period": "noon", "resource_type": "restaurant", "resource_id": 2000 + i, "name": f"Restaurant {i}", "estimated_cost": 100}
                ],
                "hotel": {"resource_type": "hotel", "resource_id": 3000 + i, "name": f"Hotel {i}", "estimated_cost": 300},
                "daily_estimated_cost": 500,
            }
            for i in range(1, days + 1)
        ],
        "tips": ["Tip 1"],
        "assumptions": ["Assumption 1"],
    }


class TestStructuredTravelPlan:
    def test_valid_1_day_plan(self):
        plan = StructuredTravelPlan.model_validate(_make_valid_plan(1))
        assert plan.days == 1
        assert len(plan.itinerary) == 1

    def test_valid_3_day_plan(self):
        plan = StructuredTravelPlan.model_validate(_make_valid_plan(3))
        assert plan.days == 3
        assert len(plan.itinerary) == 3

    def test_days_itinerary_mismatch(self):
        data = _make_valid_plan(3)
        data["days"] = 2  # 请求 2 天但 itinerary 有 3 天
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)

    def test_day_numbers_not_sequential(self):
        data = _make_valid_plan(2)
        data["itinerary"][0]["day"] = 2
        data["itinerary"][1]["day"] = 1
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)

    def test_negative_cost_rejected(self):
        data = _make_valid_plan(1)
        data["budget"]["estimated_total"] = -100
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)

    def test_invalid_period_rejected(self):
        data = _make_valid_plan(1)
        data["itinerary"][0]["items"][0]["period"] = "midnight"
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)

    def test_invalid_resource_type_rejected(self):
        data = _make_valid_plan(1)
        data["itinerary"][0]["items"][0]["resource_type"] = "taxi"
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)

    def test_empty_title_rejected(self):
        data = _make_valid_plan(1)
        data["title"] = ""
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)

    def test_days_zero_rejected(self):
        data = _make_valid_plan(1)
        data["days"] = 0
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)

    def test_optional_fields_null(self):
        data = _make_valid_plan(1)
        data["summary"] = None
        data["itinerary"][0]["summary"] = None
        data["itinerary"][0]["items"][0]["reason"] = None
        data["itinerary"][0]["items"][0]["transport_to_next"] = None
        plan = StructuredTravelPlan.model_validate(data)
        assert plan.summary is None

    def test_budget_breakdown(self):
        data = _make_valid_plan(1)
        plan = StructuredTravelPlan.model_validate(data)
        assert plan.budget.breakdown.tickets == 100
        assert plan.budget.breakdown.food == 300

    def test_get_all_resource_ids(self):
        data = _make_valid_plan(2)
        plan = StructuredTravelPlan.model_validate(data)
        ids = plan.get_all_resource_ids()
        assert 1001 in ids["scenic_spot"]
        assert 1002 in ids["scenic_spot"]
        assert 2001 in ids["restaurant"]
        assert 3001 in ids["hotel"]

    def test_days_exceeds_maximum(self):
        data = _make_valid_plan(11)  # max is 10
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)

    def test_items_per_day_limit(self):
        data = _make_valid_plan(1)
        data["itinerary"][0]["items"] = [
            {"period": "morning", "resource_type": "general_activity", "name": f"Activity {i}", "estimated_cost": 10}
            for i in range(13)  # max is 12
        ]
        with pytest.raises(Exception):
            StructuredTravelPlan.model_validate(data)
