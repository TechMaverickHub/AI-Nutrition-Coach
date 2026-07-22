"""Dashboard service: per-day nutrition summary for a user."""

import uuid
from datetime import UTC, date, datetime, time, timedelta

from app.repositories.goal import GoalRepository
from app.repositories.meal import MealRepository
from app.schemas.dashboard import DashboardRead, GoalRead, NutritionTotals


class DashboardService:
    """Composes consumed totals with the user's goal into a daily summary."""

    def __init__(
        self,
        meal_repository: MealRepository,
        goal_repository: GoalRepository,
    ) -> None:
        self._meals = meal_repository
        self._goals = goal_repository

    async def get_summary(
        self,
        user_id: uuid.UUID,
        day: date | None = None,
    ) -> DashboardRead:
        """Summarize ``day`` (defaults to the current UTC day) for ``user_id``."""
        target_day = day or datetime.now(UTC).date()
        start = datetime.combine(target_day, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)

        aggregate = await self._meals.aggregate_for_period(user_id, start, end)
        goal = await self._goals.get_by_user(user_id)

        totals = NutritionTotals(
            calories=aggregate.calories,
            protein=aggregate.protein,
            carbs=aggregate.carbs,
            fat=aggregate.fat,
        )

        goal_dto: GoalRead | None = None
        remaining: NutritionTotals | None = None
        if goal is not None:
            goal_dto = GoalRead.model_validate(goal)
            # May be negative when a target has been exceeded; not clamped so the
            # client can surface an overage.
            remaining = NutritionTotals(
                calories=goal.daily_calories - aggregate.calories,
                protein=goal.protein_goal - aggregate.protein,
                carbs=goal.carb_goal - aggregate.carbs,
                fat=goal.fat_goal - aggregate.fat,
            )

        return DashboardRead(
            date=target_day,
            meal_count=aggregate.meal_count,
            totals=totals,
            goal=goal_dto,
            remaining=remaining,
        )
