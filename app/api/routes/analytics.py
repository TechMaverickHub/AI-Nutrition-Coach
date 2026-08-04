"""Analytics route."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_analytics_service, get_current_user
from app.models.user import User
from app.schemas.analytics import AnalyticsRead
from app.services.analytics import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsRead)
async def get_analytics(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsRead:
    return await service.get_analytics(current_user.id, days)
