"""Chat client seam.

``OpenAIChatClient`` is the only module that imports the OpenAI SDK, so the rest
of the codebase depends on the :class:`ChatJSONClient` protocol and tests can
inject a fake without touching the network.
"""

import logging
from typing import Any, Protocol

from app.core.config import Settings
from app.services.ai.errors import AIUnavailableError

logger = logging.getLogger(__name__)


class ChatJSONClient(Protocol):
    """Returns the model's raw JSON string for a schema-constrained request."""

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_content: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> str: ...


class OpenAIChatClient:
    """OpenAI adapter using structured (json_schema) output."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise AIUnavailableError()
        # Imported lazily so the SDK is only required when AI is configured.
        from openai import AsyncOpenAI

        self._model = settings.openai_model
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_content: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> str:
        from openai import OpenAIError

        logger.info(
            "OpenAI request model=%s schema=%s input_chars=%d",
            self._model,
            schema_name,
            len(user_content),
        )
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    },
                },
            )
        except OpenAIError as exc:
            logger.error("OpenAI request failed: %s", exc)
            raise AIUnavailableError() from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            logger.error("OpenAI returned an empty completion")
            raise AIUnavailableError()
        return content
