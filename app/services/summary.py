"""Weekly summary service: deterministic stats narrated by an LLM."""

import logging
import uuid

from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from app.schemas.analytics import AnalyticsRead
from app.schemas.summary import WeeklyInsights, WeeklySummaryRead
from app.services.ai.errors import AIResponseError, AIUnavailableError
from app.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

_WEEK = 7

_EMPTY_WEEK = WeeklyInsights(
    narrative=(
        "You haven't logged any meals this week yet. Start logging to get a "
        "personalized recap of your nutrition."
    ),
    insights=[],
    suggestion="Log your next meal by describing it or snapping a photo.",
)


class SummaryService:
    """Builds the weekly summary by pairing analytics stats with generated prose."""

    def __init__(
        self,
        analytics_service: AnalyticsService,
        chain: Runnable[dict[str, str], WeeklyInsights],
    ) -> None:
        self._analytics = analytics_service
        self._chain = chain

    async def get_weekly(self, user_id: uuid.UUID) -> WeeklySummaryRead:
        """Return an AI-written recap of the user's last 7 days."""
        analytics = await self._analytics.get_analytics(user_id, _WEEK)

        if analytics.summary.days_logged == 0:
            insights = _EMPTY_WEEK  # no data → no LLM call
        else:
            insights = await self._generate(self._format(analytics))

        return WeeklySummaryRead(
            start_date=analytics.start_date,
            end_date=analytics.end_date,
            stats=analytics.summary,
            goal=analytics.goal,
            narrative=insights.narrative,
            insights=insights.insights,
            suggestion=insights.suggestion,
        )

    async def _generate(self, context: str) -> WeeklyInsights:
        try:
            return await self._chain.ainvoke({"context": context})
        except (OutputParserException, ValidationError) as exc:
            logger.error("Weekly summary returned unusable output: %s", exc)
            raise AIResponseError() from exc
        except Exception as exc:  # noqa: BLE001 - upstream/provider failure
            logger.error("Weekly summary request failed: %s", exc)
            raise AIUnavailableError() from exc

    @staticmethod
    def _format(a: AnalyticsRead) -> str:
        s = a.summary
        lines = [
            f"Week: {a.start_date.isoformat()} to {a.end_date.isoformat()} (7 days).",
            f"Days logged: {s.days_logged} of 7. Total meals: {s.total_meals}.",
            f"Average per day: {s.avg_calories} kcal, protein {s.avg_protein}g, "
            f"carbs {s.avg_carbs}g, fat {s.avg_fat}g.",
        ]
        if a.goal is not None:
            lines.append(
                f"Goal: {a.goal.daily_calories} kcal/day, protein {a.goal.protein_goal}g, "
                f"carbs {a.goal.carb_goal}g, fat {a.goal.fat_goal}g."
            )
            if s.days_on_target is not None:
                lines.append(
                    f"Days within the calorie goal: {s.days_on_target} of "
                    f"{s.days_logged} logged."
                )
        else:
            lines.append("The user has not set a nutrition goal.")
        per_day = ", ".join(f"{p.date.isoformat()}={p.calories}" for p in a.daily)
        lines.append(f"Daily calories: {per_day}.")
        return "\n".join(lines)
