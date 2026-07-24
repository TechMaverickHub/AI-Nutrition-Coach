"""Tests for AI text analysis.

The LangChain chain is replaced with a fake ``RunnableLambda`` so the suite runs
without a network or API key. The fake receives the same ``{"description": ...}``
input the real chain would, and returns (or raises) whatever the test needs.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda

from app.api.deps import get_current_user, get_nutrition_ai_service
from app.core.database import get_db
from app.main import create_app
from app.models.user import User
from app.schemas.ai import AnalyzedFoodItem, NutritionAnalysis
from app.services.ai.errors import AIResponseError
from app.services.ai.nutrition import NutritionAIService
from app.services.ai.prompts import PromptNotFoundError, load_prompt

from .conftest import _override_get_db


def _analysis(confidence: float | None = 0.85) -> NutritionAnalysis:
    return NutritionAnalysis(
        food_items=[
            AnalyzedFoodItem(
                name="Grilled chicken",
                calories=250,
                protein=Decimal("30"),
                carbs=Decimal("0"),
                fat=Decimal("12"),
                confidence=0.9,
            ),
            AnalyzedFoodItem(
                name="Rice",
                calories=200,
                protein=Decimal("4"),
                carbs=Decimal("45"),
                fat=Decimal("0.5"),
                confidence=0.8,
            ),
        ],
        confidence=confidence,
    )


def _client_with_chain(
    handler: Callable[[dict[str, str]], NutritionAnalysis],
    current_user: User,
) -> AsyncClient:
    """Build an authenticated client whose AI service uses a fake chain."""
    service = NutritionAIService(RunnableLambda(handler))
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_nutrition_ai_service] = lambda: service
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_analyze_text_returns_items_and_totals(current_user: User) -> None:
    captured: dict[str, Any] = {}

    def handler(payload: dict[str, str]) -> NutritionAnalysis:
        captured.update(payload)
        return _analysis()

    async with _client_with_chain(handler, current_user) as ac:
        response = await ac.post(
            "/ai/analyze/text", json={"description": "chicken and rice"}
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["food_items"]) == 2
    assert body["total_calories"] == 450
    assert float(body["total_protein"]) == 34.0
    assert float(body["total_fat"]) == 12.5
    assert body["confidence"] == 0.85
    # The user's description reached the chain unchanged.
    assert captured["description"] == "chicken and rice"


async def test_analyze_text_accepts_empty_food_items(current_user: User) -> None:
    def handler(_: dict[str, str]) -> NutritionAnalysis:
        return NutritionAnalysis(food_items=[], confidence=None)

    async with _client_with_chain(handler, current_user) as ac:
        response = await ac.post("/ai/analyze/text", json={"description": "a rock"})

    assert response.status_code == 200
    assert response.json()["total_calories"] == 0


async def test_analyze_text_maps_parse_error_to_502(current_user: User) -> None:
    def handler(_: dict[str, str]) -> NutritionAnalysis:
        raise OutputParserException("could not parse model output")

    async with _client_with_chain(handler, current_user) as ac:
        response = await ac.post("/ai/analyze/text", json={"description": "pizza"})

    assert response.status_code == 502
    assert response.json()["detail"] == AIResponseError.detail


async def test_analyze_text_maps_provider_error_to_503(current_user: User) -> None:
    def handler(_: dict[str, str]) -> NutritionAnalysis:
        raise RuntimeError("connection reset by peer")

    async with _client_with_chain(handler, current_user) as ac:
        response = await ac.post("/ai/analyze/text", json={"description": "pizza"})

    assert response.status_code == 503


async def test_analyze_text_validates_description(current_user: User) -> None:
    async with _client_with_chain(lambda _: _analysis(), current_user) as ac:
        assert (await ac.post("/ai/analyze/text", json={"description": ""})).status_code == 422
        assert (await ac.post("/ai/analyze/text", json={})).status_code == 422


async def test_analyze_text_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/ai/analyze/text", json={"description": "pizza"})
    assert response.status_code == 401


async def test_build_chain_raises_when_not_configured() -> None:
    """Without OPENAI_API_KEY the chain builder raises AIUnavailableError (503)."""
    from app.core.config import Settings
    from app.services.ai.chain import build_nutrition_chain
    from app.services.ai.errors import AIUnavailableError

    settings = Settings(
        DATABASE_URL="postgresql://t:t@localhost/t",  # type: ignore[call-arg]
        JWT_SECRET_KEY="x" * 32,
        OPENAI_API_KEY=None,
    )
    with pytest.raises(AIUnavailableError):
        build_nutrition_chain(settings)


def test_analyzed_food_item_quantizes_excess_precision() -> None:
    """The model may return more precision than Numeric(6, 2) stores."""
    item = AnalyzedFoodItem(
        name="Olive oil",
        calories=119,
        protein=Decimal("0"),
        carbs=Decimal("0"),
        fat=Decimal("13.4567"),
    )
    assert item.fat == Decimal("13.46")


def test_load_prompt_returns_registered_prompt() -> None:
    prompt = load_prompt("nutrition_text_analysis")
    assert "nutritionist" in prompt.lower()
    assert prompt.strip() == prompt


def test_load_prompt_rejects_unknown_name() -> None:
    with pytest.raises(PromptNotFoundError):
        load_prompt("does_not_exist")
