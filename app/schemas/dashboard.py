"""Dashboard DTOs."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.goal import GoalRead

__all__ = ["DashboardRead", "GoalRead", "NutritionTotals"]


class NutritionTotals(BaseModel):
    """Aggregated nutrition values for a period."""

    calories: int
    protein: Decimal
    carbs: Decimal
    fat: Decimal


class DashboardRead(BaseModel):
    """Per-day nutrition summary.

    ``goal`` and ``remaining`` are ``None`` when the user has no goal configured.
    ``remaining`` may be negative when a target has been exceeded.
    """

    date: date
    meal_count: int
    totals: NutritionTotals
    goal: GoalRead | None
    remaining: NutritionTotals | None
