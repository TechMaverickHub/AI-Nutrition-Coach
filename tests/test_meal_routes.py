"""Route tests for meal CRUD."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import AsyncClient

from app.models.meal import FoodItem, Meal, MealType

from .conftest import InMemoryMealRepository

_MEAL_PAYLOAD: dict[str, Any] = {
    "meal_type": "lunch",
    "meal_time": "2026-07-20T12:30:00Z",
    "food_items": [
        {"name": "Rice", "calories": 200, "protein": "4.00", "carbs": "45.00", "fat": "0.50"},
        {
            "name": "Chicken",
            "calories": 250,
            "protein": "30.00",
            "carbs": "0.00",
            "fat": "12.00",
            "confidence": 0.9,
        },
    ],
}


async def test_create_meal_returns_totals(auth_client: AsyncClient) -> None:
    response = await auth_client.post("/meal", json=_MEAL_PAYLOAD)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["meal_type"] == "lunch"
    assert len(body["food_items"]) == 2
    assert body["total_calories"] == 450
    assert float(body["total_protein"]) == 34.0
    assert float(body["total_fat"]) == 12.5


async def test_create_meal_requires_at_least_one_item(auth_client: AsyncClient) -> None:
    payload = {**_MEAL_PAYLOAD, "food_items": []}
    response = await auth_client.post("/meal", json=payload)
    assert response.status_code == 422


async def test_create_meal_rejects_negative_calories(auth_client: AsyncClient) -> None:
    payload = {
        **_MEAL_PAYLOAD,
        "food_items": [
            {"name": "Bad", "calories": -1, "protein": "0", "carbs": "0", "fat": "0"}
        ],
    }
    response = await auth_client.post("/meal", json=payload)
    assert response.status_code == 422


async def _add_foreign_meal(repository: InMemoryMealRepository) -> Meal:
    """Insert a meal belonging to a different user."""
    meal = Meal(
        user_id=uuid.uuid4(),
        meal_type=MealType.DINNER,
        meal_time=datetime.now(UTC),
        food_items=[
            FoodItem(
                name="Someone else's steak",
                calories=600,
                protein=Decimal("50.00"),
                carbs=Decimal("0.00"),
                fat=Decimal("40.00"),
                confidence=None,
            )
        ],
    )
    return await repository.create(meal)


async def test_list_meals_returns_only_own_meals(
    auth_client: AsyncClient, meal_repository: InMemoryMealRepository
) -> None:
    await auth_client.post("/meal", json=_MEAL_PAYLOAD)
    await _add_foreign_meal(meal_repository)

    response = await auth_client.get("/meal")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["total_calories"] == 450


async def test_delete_foreign_meal_returns_404(
    auth_client: AsyncClient, meal_repository: InMemoryMealRepository
) -> None:
    foreign = await _add_foreign_meal(meal_repository)

    response = await auth_client.delete(f"/meal/{foreign.id}")

    assert response.status_code == 404
    assert await meal_repository.get_by_id(foreign.id) is not None


async def test_list_meals_respects_pagination_bounds(auth_client: AsyncClient) -> None:
    assert (await auth_client.get("/meal?limit=0")).status_code == 422
    assert (await auth_client.get("/meal?limit=101")).status_code == 422
    assert (await auth_client.get("/meal?offset=-1")).status_code == 422


async def test_delete_meal_removes_it(auth_client: AsyncClient) -> None:
    created = await auth_client.post("/meal", json=_MEAL_PAYLOAD)
    meal_id = created.json()["id"]

    assert (await auth_client.delete(f"/meal/{meal_id}")).status_code == 204
    assert (await auth_client.get("/meal")).json() == []


async def test_delete_unknown_meal_returns_404(auth_client: AsyncClient) -> None:
    response = await auth_client.delete(f"/meal/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_meal_endpoints_require_authentication(client: AsyncClient) -> None:
    assert (await client.get("/meal")).status_code == 401
    assert (await client.post("/meal", json=_MEAL_PAYLOAD)).status_code == 401
