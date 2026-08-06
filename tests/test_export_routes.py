"""Route tests for the PDF export."""

from datetime import UTC, datetime
from decimal import Decimal

from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_report_service
from app.core.database import get_db
from app.main import create_app
from app.models.meal import FoodItem, Meal, MealType
from app.models.user import User
from app.services.analytics import AnalyticsService
from app.services.report import ReportService

from .conftest import InMemoryGoalRepository, InMemoryMealRepository, _override_get_db


def _client(
    current_user: User,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> AsyncClient:
    analytics = AnalyticsService(meal_repository, goal_repository)  # type: ignore[arg-type]
    service = ReportService(analytics)
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_report_service] = lambda: service
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_export_weekly_returns_pdf(
    current_user: User,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
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

    async with _client(current_user, meal_repository, goal_repository) as ac:
        response = await ac.get("/export/weekly.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000  # a real, non-trivial document


async def test_export_weekly_empty_still_renders(
    current_user: User,
    meal_repository: InMemoryMealRepository,
    goal_repository: InMemoryGoalRepository,
) -> None:
    async with _client(current_user, meal_repository, goal_repository) as ac:
        response = await ac.get("/export/weekly.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


async def test_export_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/export/weekly.pdf")).status_code == 401
