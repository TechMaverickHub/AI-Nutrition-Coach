"""Authentication service: registration, login, and token issuance/refresh.

Framework-agnostic. Domain failures are raised as :class:`AuthError` subclasses
and translated to HTTP responses by an exception handler in the API layer.
"""

import logging
import uuid

import jwt
from sqlalchemy.exc import IntegrityError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair, UserCreate

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Base class for authentication failures."""

    status_code = 400
    detail = "authentication error"


class EmailAlreadyExistsError(AuthError):
    status_code = 409
    detail = "email already registered"


class InvalidCredentialsError(AuthError):
    status_code = 401
    detail = "invalid email or password"


class InvalidTokenError(AuthError):
    status_code = 401
    detail = "invalid or expired token"


class AuthService:
    """Business logic for authentication."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    async def register(self, data: UserCreate) -> User:
        """Create a new user, or raise :class:`EmailAlreadyExistsError`."""
        if await self._users.get_by_email(data.email) is not None:
            raise EmailAlreadyExistsError()

        user = User(email=data.email, hashed_password=hash_password(data.password))
        try:
            created = await self._users.create(user)
        except IntegrityError as exc:  # unique-constraint race
            await self._users.rollback()
            raise EmailAlreadyExistsError() from exc

        logger.info("Registered user %s", created.id)
        return created

    async def authenticate(self, email: str, password: str) -> User:
        """Return the user for valid credentials, else raise ``InvalidCredentialsError``."""
        user = await self._users.get_by_email(email)
        if user is None or user.hashed_password is None:
            raise InvalidCredentialsError()
        if not verify_password(password, user.hashed_password):
            logger.warning("Failed login for email %s", email)
            raise InvalidCredentialsError()
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        """Issue an access + refresh token pair for ``user``."""
        subject = str(user.id)
        return TokenPair(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Validate a refresh token and issue a rotated token pair."""
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError as exc:
            raise InvalidTokenError() from exc

        if payload.get("type") != "refresh":
            raise InvalidTokenError()

        user = await self._resolve_subject(payload.get("sub"))
        return self.issue_tokens(user)

    async def _resolve_subject(self, subject: object) -> User:
        if not isinstance(subject, str):
            raise InvalidTokenError()
        try:
            user_id = uuid.UUID(subject)
        except ValueError as exc:
            raise InvalidTokenError() from exc

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise InvalidTokenError()
        return user
