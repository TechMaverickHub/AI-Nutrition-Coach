"""Dashboard DTOs."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class NutritionTotals(BaseModel):
    """Aggregated nutrition values for a period."""

    calories: int
    protein: Decimal
    carbs: Decimal
    fat: Decimal


class GoalRead(BaseModel):
    """A user's daily nutrition targets."""

    model_config = ConfigDict(from_attributes=True)

    daily_calories: int
    protein_goal: Decimal
    carb_goal: Decimal
    fat_goal: Decimal


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
