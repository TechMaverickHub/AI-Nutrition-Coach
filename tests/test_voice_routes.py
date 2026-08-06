"""Route tests for voice input, using a fake transcriber + fake chain (no network)."""

from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from langchain_core.runnables import RunnableLambda

from app.api.deps import get_current_user, get_voice_ai_service
from app.core.database import get_db
from app.main import create_app
from app.models.user import User
from app.schemas.ai import AnalyzedFoodItem, NutritionAnalysis
from app.services.ai.nutrition import NutritionAIService
from app.services.ai.voice import VoiceAIService

from .conftest import _override_get_db

_WAV = b"RIFF....WAVEfmt fake-audio-bytes"


class FakeTranscriber:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self._text = text
        self._error = error
        self.calls = 0

    async def transcribe(self, audio: bytes, filename: str) -> str:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._text


def _analysis() -> NutritionAnalysis:
    return NutritionAnalysis(
        food_items=[
            AnalyzedFoodItem(
                name="Grilled chicken",
                calories=250,
                protein=Decimal("30"),
                carbs=Decimal("0"),
                fat=Decimal("12"),
                confidence=0.9,
            )
        ],
        confidence=0.9,
    )


def _client(transcriber: FakeTranscriber, current_user: User) -> AsyncClient:
    # The nutrition service uses a fake chain returning a canned analysis.
    nutrition = NutritionAIService(RunnableLambda(lambda _payload: _analysis()))
    service = VoiceAIService(transcriber, nutrition)
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_voice_ai_service] = lambda: service
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_analyze_voice_returns_transcript_and_analysis(current_user: User) -> None:
    transcriber = FakeTranscriber("grilled chicken breast")
    async with _client(transcriber, current_user) as ac:
        response = await ac.post(
            "/ai/analyze/voice",
            files={"file": ("meal.wav", _WAV, "audio/wav")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transcript"] == "grilled chicken breast"
    assert body["analysis"]["total_calories"] == 250
    assert len(body["analysis"]["food_items"]) == 1


async def test_analyze_voice_empty_transcript_skips_analysis(current_user: User) -> None:
    transcriber = FakeTranscriber("   ")  # nothing said
    async with _client(transcriber, current_user) as ac:
        response = await ac.post(
            "/ai/analyze/voice",
            files={"file": ("silence.wav", _WAV, "audio/wav")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == ""
    assert body["analysis"]["food_items"] == []
    assert body["analysis"]["total_calories"] == 0


async def test_analyze_voice_rejects_non_audio(current_user: User) -> None:
    async with _client(FakeTranscriber("x"), current_user) as ac:
        response = await ac.post(
            "/ai/analyze/voice",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 415


async def test_analyze_voice_rejects_empty_file(current_user: User) -> None:
    async with _client(FakeTranscriber("x"), current_user) as ac:
        response = await ac.post(
            "/ai/analyze/voice",
            files={"file": ("meal.wav", b"", "audio/wav")},
        )
    assert response.status_code == 422


async def test_analyze_voice_maps_transcription_failure_to_503(current_user: User) -> None:
    from app.services.ai.errors import AIUnavailableError

    transcriber = FakeTranscriber(error=AIUnavailableError())
    async with _client(transcriber, current_user) as ac:
        response = await ac.post(
            "/ai/analyze/voice",
            files={"file": ("meal.wav", _WAV, "audio/wav")},
        )
    assert response.status_code == 503


async def test_analyze_voice_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/ai/analyze/voice",
        files={"file": ("meal.wav", _WAV, "audio/wav")},
    )
    assert response.status_code == 401
