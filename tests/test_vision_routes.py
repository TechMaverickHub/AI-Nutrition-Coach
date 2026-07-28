"""Tests for AI image analysis, using a fake vision chain (no network)."""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from httpx import ASGITransport, AsyncClient
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda

from app.api.deps import get_current_user, get_vision_ai_service
from app.core.database import get_db
from app.main import create_app
from app.models.user import User
from app.schemas.ai import AnalyzedFoodItem, NutritionAnalysis
from app.services.ai.errors import AIResponseError
from app.services.ai.vision import VisionAIService

from .conftest import _override_get_db

# 1x1 PNG (smallest valid image) — enough to exercise upload + encoding.
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da6360000002000154a24f6f0000000049454e44ae426082"
)


def _analysis() -> NutritionAnalysis:
    return NutritionAnalysis(
        food_items=[
            AnalyzedFoodItem(
                name="Apple",
                calories=95,
                protein=Decimal("0.5"),
                carbs=Decimal("25"),
                fat=Decimal("0.3"),
                confidence=0.9,
            )
        ],
        confidence=0.9,
    )


def _client_with_chain(
    handler: Callable[[Any], NutritionAnalysis],
    current_user: User,
) -> AsyncClient:
    service = VisionAIService(RunnableLambda(handler))
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_vision_ai_service] = lambda: service
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_analyze_image_returns_analysis(current_user: User) -> None:
    captured: dict[str, Any] = {}

    def handler(messages: Any) -> NutritionAnalysis:
        captured["messages"] = messages
        return _analysis()

    async with _client_with_chain(handler, current_user) as ac:
        response = await ac.post(
            "/ai/analyze/image",
            files={"file": ("meal.png", _PNG_BYTES, "image/png")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_calories"] == 95
    assert float(body["total_carbs"]) == 25.0
    # The chain received a system + multimodal human message containing an image block.
    messages = captured["messages"]
    assert len(messages) == 2
    human_content = messages[1].content
    assert any(part.get("type") == "image_url" for part in human_content)


async def test_analyze_image_rejects_non_image(current_user: User) -> None:
    async with _client_with_chain(lambda _: _analysis(), current_user) as ac:
        response = await ac.post(
            "/ai/analyze/image",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 415


async def test_analyze_image_rejects_empty_file(current_user: User) -> None:
    async with _client_with_chain(lambda _: _analysis(), current_user) as ac:
        response = await ac.post(
            "/ai/analyze/image",
            files={"file": ("empty.png", b"", "image/png")},
        )
    assert response.status_code == 422


async def test_analyze_image_maps_parse_error_to_502(current_user: User) -> None:
    def handler(_: Any) -> NutritionAnalysis:
        raise OutputParserException("bad output")

    async with _client_with_chain(handler, current_user) as ac:
        response = await ac.post(
            "/ai/analyze/image",
            files={"file": ("meal.png", _PNG_BYTES, "image/png")},
        )
    assert response.status_code == 502
    assert response.json()["detail"] == AIResponseError.detail


async def test_analyze_image_maps_provider_error_to_503(current_user: User) -> None:
    def handler(_: Any) -> NutritionAnalysis:
        raise RuntimeError("upstream down")

    async with _client_with_chain(handler, current_user) as ac:
        response = await ac.post(
            "/ai/analyze/image",
            files={"file": ("meal.png", _PNG_BYTES, "image/png")},
        )
    assert response.status_code == 503


async def test_analyze_image_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/ai/analyze/image",
        files={"file": ("meal.png", _PNG_BYTES, "image/png")},
    )
    assert response.status_code == 401
