"""Export routes (downloadable reports)."""

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_current_user, get_report_service
from app.models.user import User
from app.services.report import ReportService

router = APIRouter(prefix="/export", tags=["export"])


@router.get(
    "/weekly.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def export_weekly_pdf(
    current_user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
) -> Response:
    pdf = await service.generate_weekly_pdf(current_user.id, current_user.email)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="weekly-nutrition-report.pdf"'
        },
    )
