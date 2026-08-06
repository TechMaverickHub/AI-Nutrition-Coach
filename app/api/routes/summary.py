"""Weekly summary route."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_summary_service
from app.models.user import User
from app.schemas.summary import WeeklySummaryRead
from app.services.summary import SummaryService

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/weekly", response_model=WeeklySummaryRead)
async def weekly_summary(
    current_user: User = Depends(get_current_user),
    service: SummaryService = Depends(get_summary_service),
) -> WeeklySummaryRead:
    return await service.get_weekly(current_user.id)
