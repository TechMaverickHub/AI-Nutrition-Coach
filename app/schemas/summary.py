"""Weekly summary DTOs."""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.analytics import AnalyticsSummary
from app.schemas.goal import GoalRead


class WeeklyInsights(BaseModel):
    """The AI-generated prose portion of the weekly summary.

    This is the schema the model fills via ``with_structured_output`` — narrative
    text only. All numbers come from the deterministic analytics stats, not here.
    """

    narrative: str = Field(min_length=1, max_length=1200)
    insights: list[str] = Field(default_factory=list, max_length=6)
    suggestion: str = Field(min_length=1, max_length=400)


class WeeklySummaryRead(BaseModel):
    """The full weekly summary response: computed stats + generated prose."""

    start_date: date
    end_date: date
    stats: AnalyticsSummary
    goal: GoalRead | None
    narrative: str
    insights: list[str]
    suggestion: str
