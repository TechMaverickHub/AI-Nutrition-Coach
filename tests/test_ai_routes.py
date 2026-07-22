"""Tests for AI text analysis, using an injected fake chat client (no network)."""

import json
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_nutrition_ai_service
from app.core.database import get_db
from app.main import create_app
from app.models.user import User
from app.services.ai.errors import AIResponseError
from app.services.ai.nutrition import NutritionAIService
from app.services.ai.prompts import PromptNotFoundError, load_prompt

from .conftest import _override_get_db

_VALID_PAYLOAD = {
    "food_items": [
        {
            "name": "Grilled chicken",
            "calories": 250,
            "protein": 30,
            "carbs": 0,
            "fat": 12,
            "confidence": 0.9,
        },
        {
            "name": "Rice",
            "calories": 200,
            "protein": 4,
            "carbs": 45,
            "fat": 0.5,
            "confidence": 0.8,
        },
    ],
    "confidence": 0.85,
}


class FakeChatClient:
    """Returns a canned response and records the call."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_content: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_content": user_content,
                "schema_name": schema_name,
                "schema": schema,
            }
        )
        return self._response


def _client_with_ai(response: str, current_user: User) -> tuple[AsyncClient, FakeChatClient]:
    fake = FakeChatClient(response)
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_nutrition_ai_service] = lambda: NutritionAIService(fake)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test"), fake


async def test_analyze_text_returns_items_and_totals(current_user: User) -> None:
    http, fake = _client_with_ai(json.dumps(_VALID_PAYLOAD), current_user)
    async with http as ac:
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
    # The description was forwarded and the prompt came from prompts.md.
    assert fake.calls[0]["user_content"] == "chicken and rice"
    assert "nutritionist" in fake.calls[0]["system_prompt"].lower()


async def test_analyze_text_quantizes_excess_precision(current_user: User) -> None:
    payload = {
        "food_items": [
            {
                "name": "Olive oil",
                "calories": 119,
                "protein": 0,
                "carbs": 0,
                "fat": 13.4567,
                "confidence": None,
            }
        ],
        "confidence": None,
    }
    http, _ = _client_with_ai(json.dumps(payload), current_user)
    async with http as ac:
        response = await ac.post("/ai/analyze/text", json={"description": "olive oil"})

    assert response.status_code == 200
    assert float(response.json()["food_items"][0]["fat"]) == 13.46


async def test_analyze_text_handles_non_json_response(current_user: User) -> None:
    http, _ = _client_with_ai("I'm sorry, I cannot help with that.", current_user)
    async with http as ac:
        response = await ac.post("/ai/analyze/text", json={"description": "pizza"})

    assert response.status_code == 502
    assert response.json()["detail"] == AIResponseError.detail


async def test_analyze_text_rejects_schema_invalid_payload(current_user: User) -> None:
    bad = {"food_items": [{"name": "X", "calories": -5, "protein": 1, "carbs": 1, "fat": 1}]}
    http, _ = _client_with_ai(json.dumps(bad), current_user)
    async with http as ac:
        response = await ac.post("/ai/analyze/text", json={"description": "pizza"})

    assert response.status_code == 502


async def test_analyze_text_accepts_empty_food_items(current_user: User) -> None:
    http, _ = _client_with_ai(
        json.dumps({"food_items": [], "confidence": None}), current_user
    )
    async with http as ac:
        response = await ac.post("/ai/analyze/text", json={"description": "a rock"})

    assert response.status_code == 200
    assert response.json()["total_calories"] == 0


async def test_analyze_text_validates_description(current_user: User) -> None:
    http, _ = _client_with_ai(json.dumps(_VALID_PAYLOAD), current_user)
    async with http as ac:
        assert (await ac.post("/ai/analyze/text", json={"description": ""})).status_code == 422
        assert (await ac.post("/ai/analyze/text", json={})).status_code == 422


async def test_analyze_text_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/ai/analyze/text", json={"description": "pizza"})
    assert response.status_code == 401


async def test_ai_returns_503_when_not_configured(client: AsyncClient) -> None:
    """Without OPENAI_API_KEY the real provider raises AIUnavailableError."""
    from app.core.config import Settings
    from app.services.ai.client import OpenAIChatClient
    from app.services.ai.errors import AIUnavailableError

    settings = Settings(
        DATABASE_URL="postgresql://t:t@localhost/t",  # type: ignore[call-arg]
        JWT_SECRET_KEY="x" * 32,
        OPENAI_API_KEY=None,
    )
    with pytest.raises(AIUnavailableError):
        OpenAIChatClient(settings)


def test_load_prompt_returns_registered_prompt() -> None:
    prompt = load_prompt("nutrition_text_analysis")
    assert "nutritionist" in prompt.lower()
    assert prompt.strip() == prompt


def test_load_prompt_rejects_unknown_name() -> None:
    with pytest.raises(PromptNotFoundError):
        load_prompt("does_not_exist")
