"""AI analysis routes."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_nutrition_ai_service
from app.models.user import User
from app.schemas.ai import NutritionAnalysis, TextAnalysisRequest
from app.services.ai.nutrition import NutritionAIService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze/text", response_model=NutritionAnalysis)
async def analyze_text(
    data: TextAnalysisRequest,
    current_user: User = Depends(get_current_user),
    service: NutritionAIService = Depends(get_nutrition_ai_service),
) -> NutritionAnalysis:
    return await service.analyze_text(data.description)
