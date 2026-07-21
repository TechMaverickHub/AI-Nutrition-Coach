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
from datetime import UTC, datetime  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.api.deps import get_user_repository  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.user import User  # noqa: E402


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


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


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
