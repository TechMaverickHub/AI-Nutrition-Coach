"""Nutrition estimation from natural language, backed by an LLM."""

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.schemas.ai import NutritionAnalysis
from app.services.ai.client import ChatJSONClient
from app.services.ai.errors import AIResponseError
from app.services.ai.prompts import load_prompt

logger = logging.getLogger(__name__)

_PROMPT_NAME = "nutrition_text_analysis"
_SCHEMA_NAME = "nutrition_analysis"

# Hand-written rather than derived from the DTO: OpenAI structured outputs require
# every property listed in `required` and `additionalProperties: false`, which the
# generated Pydantic schema does not satisfy.
_NULLABLE_CONFIDENCE: dict[str, Any] = {
    "type": ["number", "null"],
    "minimum": 0,
    "maximum": 1,
}

_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["food_items", "confidence"],
    "properties": {
        "food_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "calories",
                    "protein",
                    "carbs",
                    "fat",
                    "confidence",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "calories": {"type": "integer", "minimum": 0},
                    "protein": {"type": "number", "minimum": 0},
                    "carbs": {"type": "number", "minimum": 0},
                    "fat": {"type": "number", "minimum": 0},
                    "confidence": _NULLABLE_CONFIDENCE,
                },
            },
        },
        "confidence": _NULLABLE_CONFIDENCE,
    },
}


class NutritionAIService:
    """Turns a meal description into a validated :class:`NutritionAnalysis`."""

    def __init__(self, client: ChatJSONClient) -> None:
        self._client = client

    async def analyze_text(self, description: str) -> NutritionAnalysis:
        """Estimate nutrition for ``description``.

        Raises :class:`AIResponseError` when the model returns non-JSON or a
        payload that fails validation, so malformed output never propagates.
        """
        raw = await self._client.complete_json(
            system_prompt=load_prompt(_PROMPT_NAME),
            user_content=description,
            schema_name=_SCHEMA_NAME,
            schema=_ANALYSIS_SCHEMA,
        )

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("AI returned non-JSON content (%d chars)", len(raw))
            raise AIResponseError() from exc

        try:
            analysis = NutritionAnalysis.model_validate(payload)
        except ValidationError as exc:
            logger.error("AI payload failed validation: %s", exc)
            raise AIResponseError() from exc

        logger.info(
            "Analyzed description chars=%d items=%d",
            len(description),
            len(analysis.food_items),
        )
        return analysis
