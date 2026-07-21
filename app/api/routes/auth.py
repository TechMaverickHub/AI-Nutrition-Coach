"""Authentication routes."""

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserCreate
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    user = await service.register(data)
    return service.issue_tokens(user)


@router.post("/login", response_model=TokenPair)
async def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    user = await service.authenticate(data.email, data.password)
    return service.issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return await service.refresh(data.refresh_token)
