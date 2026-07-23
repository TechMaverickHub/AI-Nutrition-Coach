"""Goal routes. Scoped to the authenticated user."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_goal_service
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalRead, GoalUpsert
from app.services.goal import GoalService

router = APIRouter(prefix="/goal", tags=["goal"])


@router.get("", response_model=GoalRead)
async def read_goal(
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
) -> Goal:
    return await service.get_goal(current_user.id)


@router.put("", response_model=GoalRead)
async def upsert_goal(
    data: GoalUpsert,
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
) -> Goal:
    return await service.set_goal(current_user.id, data)
