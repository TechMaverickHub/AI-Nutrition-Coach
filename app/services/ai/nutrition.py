"""Nutrition estimation from natural language, backed by a LangChain chain."""

import logging

from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from app.schemas.ai import NutritionAnalysis
from app.services.ai.errors import AIResponseError, AIUnavailableError

logger = logging.getLogger(__name__)


class NutritionAIService:
    """Turns a meal description into a validated :class:`NutritionAnalysis`.

    Depends on a LangChain ``Runnable`` (built by ``build_nutrition_chain``), so
    tests can inject a fake chain and run without a network or API key.
    """

    def __init__(self, chain: Runnable[dict[str, str], NutritionAnalysis]) -> None:
        self._chain = chain

    async def analyze_text(self, description: str) -> NutritionAnalysis:
        """Estimate nutrition for ``description``.

        LangChain parses and validates the model's reply, so this method only
        invokes the chain and maps failures to domain errors:

        - a malformed / schema-invalid model reply -> :class:`AIResponseError` (502)
        - a provider or network failure -> :class:`AIUnavailableError` (503)
        """
        try:
            analysis = await self._chain.ainvoke({"description": description})
        except (OutputParserException, ValidationError) as exc:
            logger.error("AI returned an unusable response: %s", exc)
            raise AIResponseError() from exc
        except Exception as exc:  # noqa: BLE001 - upstream/provider failure
            logger.error("AI request failed: %s", exc)
            raise AIUnavailableError() from exc

        logger.info(
            "Analyzed description chars=%d items=%d",
            len(description),
            len(analysis.food_items),
        )
        return analysis
