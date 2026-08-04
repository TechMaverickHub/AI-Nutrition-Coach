"""Route tests for analytics trends + summary."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient

from app.models.goal import Goal
from app.models.meal import FoodItem, Meal, MealType
from app.models.user import User

from .conftest import InMemoryGoalRepository, InMemoryMealRepository


async def _log_meal(
    repo: InMemoryMealRepository, user: User, when: datetime, calories: int
) -> None:
    await repo.create(
        Meal(
            user_id=user.id,
            meal_type=MealType.LUNCH,
            meal_time=when,
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


async def test_analytics_empty_range_is_zero_filled(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/analytics?days=7")

    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 7
    assert len(body["daily"]) == 7  # continuous, one point per day
    assert all(p["calories"] == 0 and p["meal_count"] == 0 for p in body["daily"])
    assert body["summary"]["days_logged"] == 0
    assert body["summary"]["total_meals"] == 0
    assert body["summary"]["avg_calories"] == 0
    assert body["goal"] is None
    assert body["summary"]["days_on_target"] is None


async def test_analytics_aggregates_today_and_yesterday(
    auth_client: AsyncClient, meal_repository: InMemoryMealRepository, current_user: User
) -> None:
    now = datetime.now(UTC)
    await _log_meal(meal_repository, current_user, now, 500)
    await _log_meal(meal_repository, current_user, now, 300)  # same day, 2nd meal
    await _log_meal(meal_repository, current_user, now - timedelta(days=1), 400)

    body = (await auth_client.get("/analytics?days=7")).json()

    assert len(body["daily"]) == 7
    today = body["daily"][-1]
    yesterday = body["daily"][-2]
    assert today["calories"] == 800
    assert today["meal_count"] == 2
    assert yesterday["calories"] == 400
    assert body["summary"]["total_meals"] == 3
    assert body["summary"]["days_logged"] == 2
    # avg over the full 7-day window: (800 + 400) / 7 = 171.4 -> 171
    assert body["summary"]["avg_calories"] == 171


async def test_analytics_days_on_target_against_goal(
    auth_client: AsyncClient,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
    current_user: User,
) -> None:
    goal_repository.set_goal(
        Goal(
            user_id=current_user.id,
            daily_calories=1000,
            protein_goal=Decimal("150"),
            carb_goal=Decimal("200"),
            fat_goal=Decimal("60"),
        )
    )
    now = datetime.now(UTC)
    await _log_meal(meal_repository, current_user, now, 800)  # under goal → on target
    await _log_meal(meal_repository, current_user, now - timedelta(days=1), 1500)  # over

    body = (await auth_client.get("/analytics?days=7")).json()

    assert body["goal"]["daily_calories"] == 1000
    assert body["summary"]["days_logged"] == 2
    assert body["summary"]["days_on_target"] == 1


async def test_analytics_excludes_days_outside_window(
    auth_client: AsyncClient, meal_repository: InMemoryMealRepository, current_user: User
) -> None:
    now = datetime.now(UTC)
    await _log_meal(meal_repository, current_user, now, 500)
    await _log_meal(meal_repository, current_user, now - timedelta(days=10), 900)  # outside 7

    body = (await auth_client.get("/analytics?days=7")).json()

    assert body["summary"]["total_meals"] == 1
    assert body["summary"]["days_logged"] == 1


async def test_analytics_validates_days_param(auth_client: AsyncClient) -> None:
    assert (await auth_client.get("/analytics?days=0")).status_code == 422
    assert (await auth_client.get("/analytics?days=91")).status_code == 422
    assert (await auth_client.get("/analytics?days=abc")).status_code == 422


async def test_analytics_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/analytics")).status_code == 401
