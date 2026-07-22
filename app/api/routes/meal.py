"""Meal management routes. All endpoints are scoped to the authenticated user."""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_meal_service
from app.models.meal import Meal
from app.models.user import User
from app.schemas.meal import MealCreate, MealRead
from app.services.meal import MealService

router = APIRouter(prefix="/meal", tags=["meal"])


@router.post("", response_model=MealRead, status_code=status.HTTP_201_CREATED)
async def create_meal(
    data: MealCreate,
    current_user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> Meal:
    return await service.create_meal(current_user.id, data)


@router.get("", response_model=list[MealRead])
async def list_meals(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> list[Meal]:
    return await service.list_meals(current_user.id, limit, offset)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> None:
    await service.delete_meal(current_user.id, meal_id)
