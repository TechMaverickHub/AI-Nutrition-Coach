"""Prompt registry.

Prompts live here rather than in a markdown file so they are version-controlled
and ship with the application package (the repository's ``.gitignore`` excludes
``*.md``, and a runtime dependency on an untracked file would break deploys).

Prompt text is kept as module-level constants and reached through
:func:`load_prompt`; nothing outside this module embeds prompt text.
"""

NUTRITION_TEXT_ANALYSIS = """\
You are an expert nutritionist.

Given a meal description, estimate the nutrition of each distinct food item you can
identify.

Rules:

- Break the meal into individual food items.
- Estimate calories (whole number), and protein, carbohydrates, and fat in grams.
- Assume typical serving sizes when quantities are not stated.
- `confidence` is your certainty for that item, from 0 to 1.
- Never return negative values.
- If the description contains no recognizable food, return an empty `food_items` list.

Return ONLY valid JSON matching the provided schema.\
"""

NUTRITION_IMAGE_ANALYSIS = """\
You are an expert nutritionist analysing a photo of a meal.

Identify each distinct food item you can see and estimate its nutrition.

Rules:

- List each visible food item separately.
- Estimate calories (whole number), and protein, carbohydrates, and fat in grams.
- Judge portion sizes from the image; assume typical servings when unsure.
- `confidence` is your certainty for that item, from 0 to 1 — lower it when the image is
  unclear, partially hidden, or ambiguous.
- Never return negative values.
- If the image contains no recognizable food, return an empty `food_items` list.

Return ONLY valid JSON matching the provided schema.\
"""

_PROMPTS: dict[str, str] = {
    "nutrition_text_analysis": NUTRITION_TEXT_ANALYSIS,
    "nutrition_image_analysis": NUTRITION_IMAGE_ANALYSIS,
}


class PromptNotFoundError(LookupError):
    """Raised when a named prompt is not registered."""


def load_prompt(name: str) -> str:
    """Return the registered prompt text for ``name``."""
    try:
        return _PROMPTS[name]
    except KeyError as exc:
        raise PromptNotFoundError(f"prompt '{name}' is not registered") from exc
