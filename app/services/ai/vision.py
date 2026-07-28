"""Nutrition estimation from a food photo, backed by a multimodal LangChain chain."""

import base64
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from app.schemas.ai import NutritionAnalysis
from app.services.ai.nutrition import run_analysis
from app.services.ai.prompts import load_prompt

logger = logging.getLogger(__name__)

_PROMPT_NAME = "nutrition_image_analysis"


class VisionAIService:
    """Turns a meal photo into a validated :class:`NutritionAnalysis`.

    Depends on a LangChain ``Runnable`` (the structured vision model), so tests can
    inject a fake chain and run without a network or API key.
    """

    def __init__(self, chain: Runnable[list[Any], NutritionAnalysis]) -> None:
        self._chain = chain

    async def analyze_image(self, image_bytes: bytes, mime_type: str) -> NutritionAnalysis:
        """Estimate nutrition from raw image bytes of the given ``mime_type``."""
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{encoded}"

        messages = [
            SystemMessage(load_prompt(_PROMPT_NAME)),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Identify the foods in this photo and estimate nutrition.",
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            ),
        ]

        analysis = await run_analysis(self._chain, messages)
        logger.info(
            "Analyzed image bytes=%d items=%d", len(image_bytes), len(analysis.food_items)
        )
        return analysis
