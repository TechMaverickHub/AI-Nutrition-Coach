"""Route tests for goal read/upsert."""

from typing import Any

from httpx import AsyncClient

_GOAL: dict[str, Any] = {
    "daily_calories": 2000,
    "protein_goal": "150.00",
    "carb_goal": "200.00",
    "fat_goal": "60.00",
}


async def test_get_goal_returns_404_when_unset(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/goal")
    assert response.status_code == 404
    assert response.json()["detail"] == "goal not found"


async def test_put_goal_creates_it(auth_client: AsyncClient) -> None:
    response = await auth_client.put("/goal", json=_GOAL)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["daily_calories"] == 2000
    assert float(body["protein_goal"]) == 150.0


async def test_get_goal_returns_stored_goal(auth_client: AsyncClient) -> None:
    await auth_client.put("/goal", json=_GOAL)

    body = (await auth_client.get("/goal")).json()
    assert body["daily_calories"] == 2000
    assert float(body["carb_goal"]) == 200.0


async def test_put_goal_replaces_existing(auth_client: AsyncClient) -> None:
    await auth_client.put("/goal", json=_GOAL)
    updated = {**_GOAL, "daily_calories": 2500, "fat_goal": "70.00"}

    response = await auth_client.put("/goal", json=updated)

    assert response.status_code == 200
    assert response.json()["daily_calories"] == 2500
    # A second PUT must not create a duplicate; GET reflects the new values.
    body = (await auth_client.get("/goal")).json()
    assert body["daily_calories"] == 2500
    assert float(body["fat_goal"]) == 70.0


async def test_put_goal_quantizes_excess_precision(auth_client: AsyncClient) -> None:
    response = await auth_client.put("/goal", json={**_GOAL, "protein_goal": "150.5555"})
    assert response.status_code == 200
    assert float(response.json()["protein_goal"]) == 150.56


async def test_put_goal_validation(auth_client: AsyncClient) -> None:
    assert (await auth_client.put("/goal", json={**_GOAL, "daily_calories": 0})).status_code == 422
    assert (await auth_client.put("/goal", json={**_GOAL, "protein_goal": "-1"})).status_code == 422
    assert (await auth_client.put("/goal", json={"daily_calories": 2000})).status_code == 422


async def test_goal_endpoints_require_authentication(client: AsyncClient) -> None:
    assert (await client.get("/goal")).status_code == 401
    assert (await client.put("/goal", json=_GOAL)).status_code == 401


async def test_dashboard_populates_goal_and_remaining_after_upsert(
    auth_client: AsyncClient,
) -> None:
    """The gap from Task 005: goal/remaining were unreachable via the public API."""
    before = (await auth_client.get("/dashboard?date=2026-07-20")).json()
    assert before["goal"] is None
    assert before["remaining"] is None

    await auth_client.put("/goal", json=_GOAL)
    await auth_client.post(
        "/meal",
        json={
            "meal_type": "lunch",
            "meal_time": "2026-07-20T12:00:00Z",
            "food_items": [
                {
                    "name": "Rice",
                    "calories": 200,
                    "protein": "4.00",
                    "carbs": "45.00",
                    "fat": "0.50",
                }
            ],
        },
    )

    after = (await auth_client.get("/dashboard?date=2026-07-20")).json()
    assert after["goal"]["daily_calories"] == 2000
    assert after["remaining"]["calories"] == 1800
    assert float(after["remaining"]["protein"]) == 146.0
