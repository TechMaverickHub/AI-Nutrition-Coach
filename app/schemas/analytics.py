"""Analytics DTOs."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.goal import GoalRead


class DailyPoint(BaseModel):
    """One day's aggregated nutrition (zero when nothing was logged)."""

    date: date
    calories: int
    protein: Decimal
    carbs: Decimal
    fat: Decimal
    meal_count: int


class AnalyticsSummary(BaseModel):
    """Aggregate stats across the whole range."""

    avg_calories: int
    avg_protein: Decimal
    avg_carbs: Decimal
    avg_fat: Decimal
    days_logged: int
    total_meals: int
    # Logged days within calorie goal; null when the user has no goal.
    days_on_target: int | None


class AnalyticsRead(BaseModel):
    """Per-day trends plus a summary for a date range."""

    start_date: date
    end_date: date
    days: int
    daily: list[DailyPoint]
    summary: AnalyticsSummary
    goal: GoalRead | None
