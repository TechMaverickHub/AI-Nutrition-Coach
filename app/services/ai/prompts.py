"""Prompt loading.

Prompts live in ``prompts.md`` (never inline in source). Each prompt is a
``## <name>`` section; the loader returns the text up to the next ``##`` heading.
"""

import re
from functools import lru_cache
from pathlib import Path

_PROMPTS_PATH = Path(__file__).resolve().parents[3] / ".claude" / "prompts.md"


class PromptNotFoundError(LookupError):
    """Raised when a named prompt section is absent from ``prompts.md``."""


@lru_cache
def load_prompt(name: str) -> str:
    """Return the prompt text stored under ``## <name>``."""
    try:
        content = _PROMPTS_PATH.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem failure
        raise PromptNotFoundError(f"cannot read {_PROMPTS_PATH}") from exc

    pattern = rf"^##\s+{re.escape(name)}\s*$(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, content, flags=re.MULTILINE | re.DOTALL)
    if match is None:
        raise PromptNotFoundError(f"prompt '{name}' not found in {_PROMPTS_PATH}")

    prompt = match.group(1).strip()
    if not prompt:
        raise PromptNotFoundError(f"prompt '{name}' is empty")
    return prompt
