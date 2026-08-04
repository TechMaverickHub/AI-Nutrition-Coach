"""Analytics service: multi-day nutrition trends and summary."""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.repositories.goal import GoalRepository
from app.repositories.meal import MealRepository, NutritionAggregate
from app.schemas.analytics import AnalyticsRead, AnalyticsSummary, DailyPoint
from app.schemas.goal import GoalRead

_ZERO = Decimal("0")
_CENTS = Decimal("0.01")
_EMPTY = NutritionAggregate(calories=0, protein=_ZERO, carbs=_ZERO, fat=_ZERO, meal_count=0)


def _avg(total: Decimal, days: int) -> Decimal:
    return (total / days).quantize(_CENTS, rounding=ROUND_HALF_UP)


class AnalyticsService:
    """Builds a continuous per-day series and range summary for a user."""

    def __init__(
        self,
        meal_repository: MealRepository,
        goal_repository: GoalRepository,
    ) -> None:
        self._meals = meal_repository
        self._goals = goal_repository

    async def get_analytics(self, user_id: uuid.UUID, days: int) -> AnalyticsRead:
        """Return per-day trends and a summary over the last ``days`` (ending today UTC)."""
        end_day = datetime.now(UTC).date()
        start_day = end_day - timedelta(days=days - 1)
        window_start = datetime.combine(start_day, time.min, tzinfo=UTC)
        window_end = datetime.combine(end_day, time.min, tzinfo=UTC) + timedelta(days=1)

        by_day = await self._meals.daily_aggregates(user_id, window_start, window_end)
        goal = await self._goals.get_by_user(user_id)

        daily = [
            self._point(start_day + timedelta(days=offset), by_day)
            for offset in range(days)
        ]
        summary = self._summarize(daily, days, goal.daily_calories if goal else None)

        return AnalyticsRead(
            start_date=start_day,
            end_date=end_day,
            days=days,
            daily=daily,
            summary=summary,
            goal=GoalRead.model_validate(goal) if goal is not None else None,
        )

    @staticmethod
    def _point(day: date, by_day: dict[date, NutritionAggregate]) -> DailyPoint:
        agg = by_day.get(day, _EMPTY)
        return DailyPoint(
            date=day,
            calories=agg.calories,
            protein=agg.protein,
            carbs=agg.carbs,
            fat=agg.fat,
            meal_count=agg.meal_count,
        )

    @staticmethod
    def _summarize(
        daily: list[DailyPoint], days: int, goal_calories: int | None
    ) -> AnalyticsSummary:
        total_cal = sum(p.calories for p in daily)
        total_p = sum((p.protein for p in daily), _ZERO)
        total_c = sum((p.carbs for p in daily), _ZERO)
        total_f = sum((p.fat for p in daily), _ZERO)
        logged = [p for p in daily if p.meal_count > 0]

        days_on_target: int | None = None
        if goal_calories is not None:
            days_on_target = sum(1 for p in logged if p.calories <= goal_calories)

        return AnalyticsSummary(
            avg_calories=round(total_cal / days),
            avg_protein=_avg(total_p, days),
            avg_carbs=_avg(total_c, days),
            avg_fat=_avg(total_f, days),
            days_logged=len(logged),
            total_meals=sum(p.meal_count for p in daily),
            days_on_target=days_on_target,
        )
