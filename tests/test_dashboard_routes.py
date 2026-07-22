"""Route tests for the dashboard summary."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import AsyncClient

from app.models.goal import Goal
from app.models.user import User

from .conftest import InMemoryGoalRepository

_DAY = "2026-07-20"

_MEAL_PAYLOAD: dict[str, Any] = {
    "meal_type": "lunch",
    "meal_time": f"{_DAY}T12:30:00Z",
    "food_items": [
        {"name": "Rice", "calories": 200, "protein": "4.00", "carbs": "45.00", "fat": "0.50"},
        {"name": "Chicken", "calories": 250, "protein": "30.00", "carbs": "0.00", "fat": "12.00"},
    ],
}


def _set_goal(repository: InMemoryGoalRepository, user: User, calories: int) -> None:
    repository.set_goal(
        Goal(
            user_id=user.id,
            daily_calories=calories,
            protein_goal=Decimal("150.00"),
            carb_goal=Decimal("200.00"),
            fat_goal=Decimal("60.00"),
        )
    )


async def test_dashboard_empty_day_returns_zeros(auth_client: AsyncClient) -> None:
    response = await auth_client.get(f"/dashboard?date={_DAY}")

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == _DAY
    assert body["meal_count"] == 0
    assert body["totals"]["calories"] == 0
    assert float(body["totals"]["protein"]) == 0.0
    assert body["goal"] is None
    assert body["remaining"] is None


async def test_dashboard_sums_meals_for_the_day(auth_client: AsyncClient) -> None:
    await auth_client.post("/meal", json=_MEAL_PAYLOAD)

    body = (await auth_client.get(f"/dashboard?date={_DAY}")).json()

    assert body["meal_count"] == 1
    assert body["totals"]["calories"] == 450
    assert float(body["totals"]["protein"]) == 34.0
    assert float(body["totals"]["fat"]) == 12.5


async def test_dashboard_excludes_other_days(auth_client: AsyncClient) -> None:
    await auth_client.post("/meal", json=_MEAL_PAYLOAD)

    body = (await auth_client.get("/dashboard?date=2026-07-21")).json()

    assert body["meal_count"] == 0
    assert body["totals"]["calories"] == 0


async def test_dashboard_computes_remaining_against_goal(
    auth_client: AsyncClient,
    goal_repository: InMemoryGoalRepository,
    current_user: User,
) -> None:
    _set_goal(goal_repository, current_user, calories=2000)
    await auth_client.post("/meal", json=_MEAL_PAYLOAD)

    body = (await auth_client.get(f"/dashboard?date={_DAY}")).json()

    assert body["goal"]["daily_calories"] == 2000
    assert body["remaining"]["calories"] == 1550
    assert float(body["remaining"]["protein"]) == 116.0


async def test_dashboard_remaining_can_go_negative(
    auth_client: AsyncClient,
    goal_repository: InMemoryGoalRepository,
    current_user: User,
) -> None:
    _set_goal(goal_repository, current_user, calories=100)
    await auth_client.post("/meal", json=_MEAL_PAYLOAD)

    body = (await auth_client.get(f"/dashboard?date={_DAY}")).json()

    assert body["remaining"]["calories"] == -350


async def test_dashboard_defaults_to_today(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/dashboard")

    assert response.status_code == 200
    assert response.json()["date"] == datetime.now(UTC).date().isoformat()


async def test_dashboard_rejects_invalid_date(auth_client: AsyncClient) -> None:
    assert (await auth_client.get("/dashboard?date=not-a-date")).status_code == 422


async def test_dashboard_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/dashboard")).status_code == 401
