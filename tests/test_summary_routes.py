"""Route tests for the weekly summary, using a fake summary chain (no network)."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import ASGITransport, AsyncClient
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda

from app.api.deps import get_current_user, get_summary_service
from app.core.database import get_db
from app.main import create_app
from app.models.meal import FoodItem, Meal, MealType
from app.models.user import User
from app.schemas.summary import WeeklyInsights
from app.services.analytics import AnalyticsService
from app.services.summary import SummaryService

from .conftest import InMemoryGoalRepository, InMemoryMealRepository, _override_get_db


def _client(
    handler: Callable[[dict[str, str]], WeeklyInsights],
    current_user: User,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> AsyncClient:
    analytics = AnalyticsService(meal_repository, goal_repository)  # type: ignore[arg-type]
    service = SummaryService(analytics, RunnableLambda(handler))
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_summary_service] = lambda: service
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _insights() -> WeeklyInsights:
    return WeeklyInsights(
        narrative="Solid week — you logged most days and stayed near your goal.",
        insights=["Protein was a little low.", "Tuesday was your best day."],
        suggestion="Add a protein-rich snack midweek.",
    )


async def _log(repo: InMemoryMealRepository, user: User, calories: int) -> None:
    await repo.create(
        Meal(
            user_id=user.id,
            meal_type=MealType.LUNCH,
            meal_time=datetime.now(UTC),
            food_items=[
                FoodItem(
                    name="Food",
                    calories=calories,
                    protein=Decimal("10"),
                    carbs=Decimal("20"),
                    fat=Decimal("5"),
                    confidence=None,
                )
            ],
        )
    )


async def test_weekly_summary_with_data(
    current_user: User,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    await _log(meal_repository, current_user, 600)
    captured: dict[str, Any] = {}

    def handler(payload: dict[str, str]) -> WeeklyInsights:
        captured.update(payload)
        return _insights()

    async with _client(handler, current_user, meal_repository, goal_repository) as ac:
        response = await ac.get("/summary/weekly")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["narrative"].startswith("Solid week")
    assert len(body["insights"]) == 2
    assert body["stats"]["total_meals"] == 1  # deterministic, from analytics
    # the model was handed the computed context, not raw meals
    assert "Days logged" in captured["context"]


async def test_weekly_summary_empty_week_skips_llm(
    current_user: User,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    called = {"n": 0}

    def handler(_payload: dict[str, str]) -> WeeklyInsights:
        called["n"] += 1
        return _insights()

    async with _client(handler, current_user, meal_repository, goal_repository) as ac:
        response = await ac.get("/summary/weekly")

    assert response.status_code == 200
    body = response.json()
    assert called["n"] == 0  # no LLM call when nothing logged
    assert "haven't logged any meals" in body["narrative"]
    assert body["insights"] == []
    assert body["stats"]["days_logged"] == 0


async def test_weekly_summary_maps_parse_error_to_502(
    current_user: User,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    await _log(meal_repository, current_user, 500)

    def handler(_payload: dict[str, str]) -> WeeklyInsights:
        raise OutputParserException("bad output")

    async with _client(handler, current_user, meal_repository, goal_repository) as ac:
        response = await ac.get("/summary/weekly")
    assert response.status_code == 502


async def test_weekly_summary_maps_provider_error_to_503(
    current_user: User,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    await _log(meal_repository, current_user, 500)

    def handler(_payload: dict[str, str]) -> WeeklyInsights:
        raise RuntimeError("provider down")

    async with _client(handler, current_user, meal_repository, goal_repository) as ac:
        response = await ac.get("/summary/weekly")
    assert response.status_code == 503


async def test_weekly_summary_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/summary/weekly")).status_code == 401
