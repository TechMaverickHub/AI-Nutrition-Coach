"""Nutrition estimation from spoken audio: transcribe, then reuse text analysis."""

import logging

from app.schemas.ai import NutritionAnalysis, VoiceAnalysisResponse
from app.services.ai.nutrition import NutritionAIService
from app.services.ai.transcribe import Transcriber

logger = logging.getLogger(__name__)


class VoiceAIService:
    """Transcribes audio and runs the transcript through nutrition text analysis."""

    def __init__(
        self,
        transcriber: Transcriber,
        nutrition_service: NutritionAIService,
    ) -> None:
        self._transcriber = transcriber
        self._nutrition = nutrition_service

    async def analyze_voice(self, audio: bytes, filename: str) -> VoiceAnalysisResponse:
        """Return the transcript and the nutrition it describes."""
        transcript = (await self._transcriber.transcribe(audio, filename)).strip()

        if not transcript:
            # Nothing recognizable was said — return an empty analysis, no LLM call.
            analysis = NutritionAnalysis(food_items=[], confidence=None)
        else:
            analysis = await self._nutrition.analyze_text(transcript)

        logger.info("Voice analysis: transcript_chars=%d", len(transcript))
        return VoiceAnalysisResponse(transcript=transcript, analysis=analysis)
