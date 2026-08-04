"""Shared pytest fixtures.

Environment defaults are set *before* the application is imported so the suite
runs hermetically without a real ``.env`` or a live PostgreSQL instance. The
database dependency and the user repository are overridden with in-memory fakes.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-for-tests-only-abcdefghijklmnop"
)

import uuid  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402
from datetime import UTC, date, datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.api.deps import (  # noqa: E402
    get_current_user,
    get_goal_repository,
    get_meal_repository,
    get_user_repository,
)
from app.core.database import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.conversation import Conversation, Message  # noqa: E402
from app.models.goal import Goal  # noqa: E402
from app.models.meal import Meal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.repositories.meal import NutritionAggregate  # noqa: E402


class _FakeSession:
    """Minimal stand-in for ``AsyncSession`` used by the health check test."""

    async def execute(self, *args: object, **kwargs: object) -> None:
        return None


async def _override_get_db() -> AsyncGenerator[_FakeSession, None]:
    yield _FakeSession()


class InMemoryUserRepository:
    """In-memory implementation of :class:`UserRepository` for tests."""

    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, User] = {}
        self._by_email: dict[str, User] = {}

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email)

    async def create(self, user: User) -> User:
        if user.id is None:
            user.id = uuid.uuid4()
        if user.created_at is None:
            user.created_at = datetime.now(UTC)
        self._by_id[user.id] = user
        self._by_email[user.email] = user
        return user

    async def rollback(self) -> None:
        return None


class InMemoryMealRepository:
    """In-memory implementation of :class:`MealRepository` for tests."""

    def __init__(self) -> None:
        self._meals: dict[uuid.UUID, Meal] = {}

    async def create(self, meal: Meal) -> Meal:
        if meal.id is None:
            meal.id = uuid.uuid4()
        if meal.created_at is None:
            meal.created_at = datetime.now(UTC)
        for item in meal.food_items:
            if item.id is None:
                item.id = uuid.uuid4()
        self._meals[meal.id] = meal
        return meal

    async def get_by_id(self, meal_id: uuid.UUID) -> Meal | None:
        return self._meals.get(meal_id)

    async def list_by_user(
        self, user_id: uuid.UUID, limit: int, offset: int
    ) -> list[Meal]:
        owned = [m for m in self._meals.values() if m.user_id == user_id]
        owned.sort(key=lambda m: m.meal_time, reverse=True)
        return owned[offset : offset + limit]

    async def delete(self, meal: Meal) -> None:
        self._meals.pop(meal.id, None)

    async def aggregate_for_period(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> NutritionAggregate:
        meals = [
            m
            for m in self._meals.values()
            if m.user_id == user_id and start <= m.meal_time < end
        ]
        items = [item for meal in meals for item in meal.food_items]
        return NutritionAggregate(
            calories=sum(item.calories for item in items),
            protein=sum((item.protein for item in items), Decimal(0)),
            carbs=sum((item.carbs for item in items), Decimal(0)),
            fat=sum((item.fat for item in items), Decimal(0)),
            meal_count=len(meals),
        )

    async def daily_aggregates(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> dict[date, NutritionAggregate]:
        buckets: dict[date, list[Meal]] = {}
        for meal in self._meals.values():
            if meal.user_id == user_id and start <= meal.meal_time < end:
                day = meal.meal_time.astimezone(UTC).date()
                buckets.setdefault(day, []).append(meal)
        result: dict[date, NutritionAggregate] = {}
        for day, meals in buckets.items():
            items = [item for meal in meals for item in meal.food_items]
            result[day] = NutritionAggregate(
                calories=sum(item.calories for item in items),
                protein=sum((item.protein for item in items), Decimal(0)),
                carbs=sum((item.carbs for item in items), Decimal(0)),
                fat=sum((item.fat for item in items), Decimal(0)),
                meal_count=len(meals),
            )
        return result


class InMemoryGoalRepository:
    """In-memory implementation of :class:`GoalRepository` for tests."""

    def __init__(self) -> None:
        self._goals: dict[uuid.UUID, Goal] = {}

    async def get_by_user(self, user_id: uuid.UUID) -> Goal | None:
        return self._goals.get(user_id)

    async def create(self, goal: Goal) -> Goal:
        if goal.id is None:
            goal.id = uuid.uuid4()
        self._goals[goal.user_id] = goal
        return goal

    async def update(self, goal: Goal) -> Goal:
        self._goals[goal.user_id] = goal
        return goal

    async def rollback(self) -> None:
        return None

    def set_goal(self, goal: Goal) -> None:
        """Test helper for seeding a goal directly."""
        self._goals[goal.user_id] = goal


class InMemoryConversationRepository:
    """In-memory implementation of :class:`ConversationRepository` for tests."""

    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, Conversation] = {}

    async def create(self, conversation: Conversation) -> Conversation:
        if conversation.id is None:
            conversation.id = uuid.uuid4()
        now = datetime.now(UTC)
        if conversation.created_at is None:
            conversation.created_at = now
        conversation.updated_at = now
        self._by_id[conversation.id] = conversation
        return conversation

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        return self._by_id.get(conversation_id)

    async def list_by_user(self, user_id: uuid.UUID) -> list[Conversation]:
        owned = [c for c in self._by_id.values() if c.user_id == user_id]
        owned.sort(key=lambda c: c.updated_at, reverse=True)
        return owned

    async def add_messages(self, *messages: Message) -> None:
        for message in messages:
            if message.id is None:
                message.id = uuid.uuid4()
            if message.created_at is None:
                message.created_at = datetime.now(UTC)
            conversation = self._by_id.get(message.conversation_id)
            if conversation is not None:
                conversation.messages.append(message)

    async def delete(self, conversation: Conversation) -> None:
        self._by_id.pop(conversation.id, None)


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def goal_repository() -> InMemoryGoalRepository:
    return InMemoryGoalRepository()


@pytest.fixture
def conversation_repository() -> InMemoryConversationRepository:
    return InMemoryConversationRepository()


@pytest.fixture
def meal_repository() -> InMemoryMealRepository:
    return InMemoryMealRepository()


@pytest.fixture
def current_user() -> User:
    user = User(email="owner@example.com", hashed_password="x")
    user.id = uuid.uuid4()
    user.created_at = datetime.now(UTC)
    return user


@pytest.fixture
async def auth_client(
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
    current_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX client with an authenticated user and in-memory repositories."""
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_meal_repository] = lambda: meal_repository
    app.dependency_overrides[get_goal_repository] = lambda: goal_repository
    app.dependency_overrides[get_current_user] = lambda: current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def client(
    user_repository: InMemoryUserRepository,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX client bound to the ASGI app with DB + user repo faked out."""
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_user_repository] = lambda: user_repository
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
