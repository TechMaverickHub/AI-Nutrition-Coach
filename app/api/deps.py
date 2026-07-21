"""Shared API dependencies (dependency injection wiring)."""

import uuid

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth import AuthService, InvalidTokenError

_bearer = HTTPBearer(auto_error=False)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_auth_service(
    repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(repository)


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
