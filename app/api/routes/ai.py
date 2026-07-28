"""AI analysis routes."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import (
    get_current_user,
    get_nutrition_ai_service,
    get_vision_ai_service,
)
from app.models.user import User
from app.schemas.ai import NutritionAnalysis, TextAnalysisRequest
from app.services.ai.nutrition import NutritionAIService
from app.services.ai.vision import VisionAIService

router = APIRouter(prefix="/ai", tags=["ai"])

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


@router.post("/analyze/text", response_model=NutritionAnalysis)
async def analyze_text(
    data: TextAnalysisRequest,
    current_user: User = Depends(get_current_user),
    service: NutritionAIService = Depends(get_nutrition_ai_service),
) -> NutritionAnalysis:
    return await service.analyze_text(data.description)


@router.post("/analyze/image", response_model=NutritionAnalysis)
async def analyze_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: VisionAIService = Depends(get_vision_ai_service),
) -> NutritionAnalysis:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="image must be JPEG, PNG, or WebP",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=422,  # Unprocessable Content
            detail="uploaded file is empty",
        )
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="image exceeds the 8 MB limit",
        )

    return await service.analyze_image(image_bytes, file.content_type)
