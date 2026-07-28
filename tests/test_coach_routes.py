"""Route tests for the AI coach, using a fake chat model (no network)."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

from app.api.deps import get_coach_service, get_current_user
from app.core.database import get_db
from app.main import create_app
from app.models.conversation import Conversation
from app.models.goal import Goal
from app.models.meal import FoodItem, Meal, MealType
from app.models.user import User
from app.services.coach import CoachService
from app.services.dashboard import DashboardService

from .conftest import (
    InMemoryConversationRepository,
    InMemoryGoalRepository,
    InMemoryMealRepository,
    _override_get_db,
)


def _client(
    handler: Callable[[list[BaseMessage]], AIMessage],
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> AsyncClient:
    dashboard = DashboardService(meal_repository, goal_repository)  # type: ignore[arg-type]
    service = CoachService(RunnableLambda(handler), conversation_repository, dashboard)  # type: ignore[arg-type]
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_coach_service] = lambda: service
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _reply(text: str = "Try adding more protein.") -> Callable[[list[BaseMessage]], AIMessage]:
    return lambda _messages: AIMessage(content=text)


async def test_chat_creates_new_conversation(
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    async with _client(
        _reply(), current_user, conversation_repository, meal_repository, goal_repository
    ) as ac:
        response = await ac.post("/coach/chat", json={"message": "What should I eat?"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"] == "Try adding more protein."
    assert uuid.UUID(body["conversation_id"])


async def test_chat_continues_and_replays_history(
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    seen: list[list[BaseMessage]] = []

    def handler(messages: list[BaseMessage]) -> AIMessage:
        seen.append(messages)
        return AIMessage(content="ok")

    async with _client(
        handler, current_user, conversation_repository, meal_repository, goal_repository
    ) as ac:
        first = await ac.post("/coach/chat", json={"message": "Hi"})
        cid = first.json()["conversation_id"]
        second = await ac.post(
            "/coach/chat", json={"message": "And now?", "conversation_id": cid}
        )

    assert second.status_code == 200
    # The second call replays the prior turn: system + user("Hi") + ai("ok") + user("And now?")
    roles = [type(m).__name__ for m in seen[1]]
    assert roles[0] == "SystemMessage"
    assert len(seen[1]) == 4
    assert "Hi" in seen[1][1].content


async def test_chat_foreign_conversation_returns_404(
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    foreign = await conversation_repository.create(
        Conversation(user_id=uuid.uuid4(), title="someone else")
    )
    async with _client(
        _reply(), current_user, conversation_repository, meal_repository, goal_repository
    ) as ac:
        response = await ac.post(
            "/coach/chat", json={"message": "hi", "conversation_id": str(foreign.id)}
        )
    assert response.status_code == 404


async def test_personalization_injects_goal_and_totals(
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    goal_repository.set_goal(
        Goal(
            user_id=current_user.id,
            daily_calories=2000,
            protein_goal=Decimal("150"),
            carb_goal=Decimal("200"),
            fat_goal=Decimal("60"),
        )
    )
    await meal_repository.create(
        Meal(
            user_id=current_user.id,
            meal_type=MealType.LUNCH,
            meal_time=datetime.now(UTC),
            food_items=[
                FoodItem(
                    name="Rice",
                    calories=200,
                    protein=Decimal("4"),
                    carbs=Decimal("45"),
                    fat=Decimal("0.5"),
                    confidence=None,
                )
            ],
        )
    )
    captured: dict[str, Any] = {}

    def handler(messages: list[BaseMessage]) -> AIMessage:
        captured["system"] = messages[0]
        return AIMessage(content="noted")

    async with _client(
        handler, current_user, conversation_repository, meal_repository, goal_repository
    ) as ac:
        response = await ac.post("/coach/chat", json={"message": "How am I doing?"})

    assert response.status_code == 200
    system = captured["system"]
    assert isinstance(system, SystemMessage)
    assert "2000 kcal" in system.content  # goal
    assert "Consumed" in system.content  # today's totals


async def test_list_and_detail_and_delete(
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    async with _client(
        _reply(), current_user, conversation_repository, meal_repository, goal_repository
    ) as ac:
        cid = (await ac.post("/coach/chat", json={"message": "Hello coach"})).json()[
            "conversation_id"
        ]

        listing = await ac.get("/coach/conversations")
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        assert listing.json()[0]["title"] == "Hello coach"

        detail = await ac.get(f"/coach/conversations/{cid}")
        assert detail.status_code == 200
        messages = detail.json()["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant"]

        assert (await ac.delete(f"/coach/conversations/{cid}")).status_code == 204
        assert (await ac.get(f"/coach/conversations/{cid}")).status_code == 404


async def test_get_foreign_conversation_returns_404(
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    foreign = await conversation_repository.create(
        Conversation(user_id=uuid.uuid4(), title="not yours")
    )
    async with _client(
        _reply(), current_user, conversation_repository, meal_repository, goal_repository
    ) as ac:
        assert (await ac.get(f"/coach/conversations/{foreign.id}")).status_code == 404
        assert (await ac.delete(f"/coach/conversations/{foreign.id}")).status_code == 404


async def test_chat_maps_model_failure_to_503(
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    def handler(_messages: list[BaseMessage]) -> AIMessage:
        raise RuntimeError("provider down")

    async with _client(
        handler, current_user, conversation_repository, meal_repository, goal_repository
    ) as ac:
        response = await ac.post("/coach/chat", json={"message": "hi"})
    assert response.status_code == 503


async def test_chat_validates_message(
    current_user: User,
    conversation_repository: InMemoryConversationRepository,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    async with _client(
        _reply(), current_user, conversation_repository, meal_repository, goal_repository
    ) as ac:
        assert (await ac.post("/coach/chat", json={"message": ""})).status_code == 422


async def test_coach_requires_authentication(client: AsyncClient) -> None:
    assert (await client.post("/coach/chat", json={"message": "hi"})).status_code == 401
    assert (await client.get("/coach/conversations")).status_code == 401
