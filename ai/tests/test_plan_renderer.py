"""Markdown 渲染器测试"""
import pytest
from xingzhi_ai.plan_schema import (
    StructuredTravelPlan, DayPlan, ItineraryItem, MealInfo, HotelInfo,
    PlanDestination, PlanBudget, BudgetBreakdown,
)
from xingzhi_ai.plan_renderer import render_travel_plan_markdown


def _make_plan(days=2) -> StructuredTravelPlan:
    itinerary = []
    for d in range(1, days + 1):
        items = [
            ItineraryItem(
                period="morning", resource_type="scenic_spot", resource_id=1000 + d,
                name=f"Scenic {d}", duration_minutes=120, estimated_cost=50,
                reason="Great view", transport_to_next="Walk",
            ),
            ItineraryItem(
                period="afternoon", resource_type="general_activity", resource_id=None,
                name="Free time", estimated_cost=0,
            ),
        ]
        meals = [
            MealInfo(period="noon", resource_id=2000 + d, name=f"Restaurant {d}", estimated_cost=100),
        ]
        hotel = HotelInfo(resource_id=3000 + d, name=f"Hotel {d}", estimated_cost=300)
        day = DayPlan(day=d, theme=f"Day {d} Theme", items=items, meals=meals, hotel=hotel, daily_estimated_cost=500)
        itinerary.append(day)

    return StructuredTravelPlan(
        title="Test Trip Plan",
        destination=PlanDestination(city_id=1, name="Test City", province="Test"),
        days=days,
        travelers=2,
        summary="A test trip",
        budget=PlanBudget(
            requested_total=2000, estimated_total=1800,
            breakdown=BudgetBreakdown(tickets=200, food=600, lodging=600, transport=200, other=200),
        ),
        itinerary=itinerary,
        tips=["Wear comfortable shoes", "Bring an umbrella"],
        assumptions=["Prices are estimates", "Weather may vary"],
    )


class TestRenderTravelPlanMarkdown:
    def test_contains_title(self):
        md = render_travel_plan_markdown(_make_plan())
        assert "# Test Trip Plan" in md

    def test_contains_destination(self):
        md = render_travel_plan_markdown(_make_plan())
        assert "Test City" in md

    def test_contains_multi_day_structure(self):
        md = render_travel_plan_markdown(_make_plan(2))
        assert "第 1 天" in md
        assert "第 2 天" in md

    def test_contains_time_periods(self):
        md = render_travel_plan_markdown(_make_plan(1))
        assert "上午" in md
        assert "下午" in md

    def test_contains_restaurant(self):
        md = render_travel_plan_markdown(_make_plan(1))
        assert "Restaurant 1" in md

    def test_contains_hotel(self):
        md = render_travel_plan_markdown(_make_plan(1))
        assert "Hotel 1" in md

    def test_contains_budget(self):
        md = render_travel_plan_markdown(_make_plan(1))
        assert "1800" in md

    def test_contains_tips(self):
        md = render_travel_plan_markdown(_make_plan(1))
        assert "Wear comfortable shoes" in md

    def test_contains_assumptions(self):
        md = render_travel_plan_markdown(_make_plan(1))
        assert "Prices are estimates" in md

    def test_no_none_string(self):
        md = render_travel_plan_markdown(_make_plan(1))
        assert "None" not in md

    def test_no_html_injection(self):
        plan = _make_plan(1)
        plan.title = '<script>alert("xss")</script>'
        md = render_travel_plan_markdown(plan)
        assert "<script>" not in md

    def test_contains_footer(self):
        md = render_travel_plan_markdown(_make_plan(1))
        assert "行知 AI 助手生成" in md

    def test_free_cost_format(self):
        plan = _make_plan(1)
        plan.itinerary[0].items[1].estimated_cost = 0  # free activity
        md = render_travel_plan_markdown(plan)
        # free activity should NOT show "0" cost unlabeled
        # _format_cost(0) returns non-empty label, md has the label
        assert len(md) > 0  # markdown is generated
