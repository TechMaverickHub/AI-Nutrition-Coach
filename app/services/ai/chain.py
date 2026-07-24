"""LangChain wiring for nutrition text analysis.

This module builds a small LangChain *chain*: a prompt piped into an OpenAI chat
model that is configured to return a validated :class:`NutritionAnalysis` object.

Beginner notes
--------------
- ``ChatOpenAI`` is LangChain's wrapper around an OpenAI chat model.
- ``ChatPromptTemplate`` is a reusable set of messages with ``{slots}``.
- ``with_structured_output(Model)`` tells the model to return JSON matching the
  Pydantic model, and LangChain parses + validates it for us — so there is no
  hand-written JSON schema, no ``json.loads`` and no ``model_validate`` here.
- ``prompt | structured`` composes the two steps into one runnable ("LCEL").
"""

from typing import cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.core.config import Settings
from app.schemas.ai import NutritionAnalysis
from app.services.ai.errors import AIUnavailableError
from app.services.ai.prompts import load_prompt

_PROMPT_NAME = "nutrition_text_analysis"


def build_nutrition_chain(settings: Settings) -> Runnable[dict[str, str], NutritionAnalysis]:
    """Build the prompt → model chain that produces a :class:`NutritionAnalysis`.

    Raises :class:`AIUnavailableError` (HTTP 503) when no API key is configured,
    so the rest of the API keeps working without AI credentials.
    """
    if not settings.openai_api_key:
        raise AIUnavailableError()

    # Imported lazily so the SDK is only required when AI is configured.
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        temperature=0,
    )

    # The model now returns a validated NutritionAnalysis instead of raw text.
    structured_model = model.with_structured_output(NutritionAnalysis)

    # The system prompt is static; the human message carries the user's description.
    # NOTE: ChatPromptTemplate treats "{" / "}" as variables. The stored prompt has
    # none — keep it that way, or escape braces as "{{" / "}}".
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt(_PROMPT_NAME)),
            ("human", "{description}"),
        ]
    )

    # with_structured_output is generically typed as returning dict | BaseModel;
    # narrow it to the concrete model we asked for.
    chain = prompt | structured_model
    return cast("Runnable[dict[str, str], NutritionAnalysis]", chain)
