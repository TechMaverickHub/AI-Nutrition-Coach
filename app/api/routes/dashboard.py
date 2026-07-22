"""Dashboard route."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_dashboard_service
from app.models.user import User
from app.schemas.dashboard import DashboardRead
from app.services.dashboard import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardRead)
async def get_dashboard(
    day: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardRead:
    return await service.get_summary(current_user.id, day)
