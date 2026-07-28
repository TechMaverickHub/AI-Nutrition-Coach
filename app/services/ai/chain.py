"""LangChain wiring for nutrition analysis (text and vision).

Both chains ask an OpenAI chat model to return a validated
:class:`NutritionAnalysis` via ``with_structured_output`` — LangChain builds the
JSON schema and parses the reply, so there is no hand-written schema here.

Beginner notes
--------------
- ``ChatOpenAI`` wraps an OpenAI chat model.
- ``with_structured_output(Model)`` returns a runnable that outputs a validated
  Pydantic object instead of raw text.
- The **text** chain is ``prompt | model`` (the prompt fills in ``{description}``).
- The **vision** chain is just the model; the caller supplies a multimodal message
  (text + image) because that is clearer than templating a data URL into a string.
"""

from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.core.config import Settings
from app.schemas.ai import NutritionAnalysis
from app.services.ai.errors import AIUnavailableError
from app.services.ai.prompts import load_prompt

_TEXT_PROMPT_NAME = "nutrition_text_analysis"


def _build_chat_model(settings: Settings, model_name: str) -> BaseChatModel:
    """Create a configured ``ChatOpenAI`` model.

    Raises :class:`AIUnavailableError` (503) when no API key is configured.
    """
    if not settings.openai_api_key:
        raise AIUnavailableError()

    # Imported lazily so the SDK is only required when AI is configured.
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model_name,
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        temperature=0,
    )


def build_nutrition_chain(settings: Settings) -> Runnable[dict[str, str], NutritionAnalysis]:
    """Build the text chain: ``prompt | model`` producing a ``NutritionAnalysis``."""
    structured_model = _build_chat_model(settings, settings.openai_model).with_structured_output(
        NutritionAnalysis
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt(_TEXT_PROMPT_NAME)),
            ("human", "{description}"),
        ]
    )
    # with_structured_output is generically typed as dict | BaseModel; narrow it.
    return cast("Runnable[dict[str, str], NutritionAnalysis]", prompt | structured_model)


def build_coach_model(settings: Settings) -> BaseChatModel:
    """Build the chat model for the coach.

    Unlike the analysis chains this returns a plain chat model (free-text reply,
    no structured output). The caller supplies the message list each turn.
    Raises :class:`AIUnavailableError` (503) when no API key is configured.
    """
    return _build_chat_model(settings, settings.openai_model)


def build_vision_chain(settings: Settings) -> Runnable[list[Any], NutritionAnalysis]:
    """Build the vision chain: the structured model alone.

    The caller (``VisionAIService``) supplies the multimodal messages, so this is
    just ``model.with_structured_output(...)``.
    """
    structured_model = _build_chat_model(
        settings, settings.openai_vision_model
    ).with_structured_output(NutritionAnalysis)
    return cast("Runnable[list[Any], NutritionAnalysis]", structured_model)
