"""Speech-to-text transcription.

Transcription is not a chat/LLM operation, so it uses the OpenAI audio API
directly rather than LangChain. ``OpenAITranscriber`` is the only place the SDK's
audio endpoint is called; the rest of the code depends on the ``Transcriber``
protocol so tests can inject a fake.
"""

import logging
from typing import Protocol

from app.core.config import Settings
from app.services.ai.errors import AIUnavailableError

logger = logging.getLogger(__name__)


class Transcriber(Protocol):
    """Turns audio bytes into text."""

    async def transcribe(self, audio: bytes, filename: str) -> str: ...


class OpenAITranscriber:
    """OpenAI speech-to-text adapter."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise AIUnavailableError()
        from openai import AsyncOpenAI

        self._model = settings.openai_transcribe_model
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )

    async def transcribe(self, audio: bytes, filename: str) -> str:
        from openai import OpenAIError

        logger.info("Transcribing audio model=%s bytes=%d", self._model, len(audio))
        try:
            result = await self._client.audio.transcriptions.create(
                model=self._model,
                file=(filename, audio),
            )
        except OpenAIError as exc:
            logger.error("Transcription failed: %s", exc)
            raise AIUnavailableError() from exc
        return result.text
