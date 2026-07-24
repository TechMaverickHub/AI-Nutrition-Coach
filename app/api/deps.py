"""Shared API dependencies (dependency injection wiring)."""

import uuid

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.repositories.goal import GoalRepository
from app.repositories.meal import MealRepository
from app.repositories.user import UserRepository
from app.services.ai.chain import build_nutrition_chain
from app.services.ai.nutrition import NutritionAIService
from app.services.auth import AuthService, InvalidTokenError
from app.services.dashboard import DashboardService
from app.services.goal import GoalService
from app.services.meal import MealService

_bearer = HTTPBearer(auto_error=False)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_auth_service(
    repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(repository)


def get_meal_repository(db: AsyncSession = Depends(get_db)) -> MealRepository:
    return MealRepository(db)


def get_meal_service(
    repository: MealRepository = Depends(get_meal_repository),
) -> MealService:
    return MealService(repository)


def get_goal_repository(db: AsyncSession = Depends(get_db)) -> GoalRepository:
    return GoalRepository(db)


def get_goal_service(
    repository: GoalRepository = Depends(get_goal_repository),
) -> GoalService:
    return GoalService(repository)


def get_dashboard_service(
    meal_repository: MealRepository = Depends(get_meal_repository),
    goal_repository: GoalRepository = Depends(get_goal_repository),
) -> DashboardService:
    return DashboardService(meal_repository, goal_repository)


def get_nutrition_ai_service(
    settings: Settings = Depends(get_settings),
) -> NutritionAIService:
    """Build the AI service.

    Raises ``AIUnavailableError`` (503) when no API key is configured, so the
    rest of the API keeps working without AI credentials.
    """
    return NutritionAIService(build_nutrition_chain(settings))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    repository: UserRepository = Depends(get_user_repository),
) -> User:
    """Resolve the authenticated user from a bearer access token."""
    if credentials is None:
        raise InvalidTokenError()

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError() from exc

    if payload.get("type") != "access":
        raise InvalidTokenError()

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise InvalidTokenError()
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise InvalidTokenError() from exc

    user = await repository.get_by_id(user_id)
    if user is None:
        raise InvalidTokenError()
    return user
