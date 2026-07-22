"""AI analysis DTOs."""

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field, computed_field, field_validator

# Upper bound matches the Numeric(6, 2) columns these values are destined for.
_MAX_MACRO = Decimal("9999.99")
_CENTS = Decimal("0.01")


class TextAnalysisRequest(BaseModel):
    """Free-text meal description to analyse."""

    description: str = Field(min_length=1, max_length=2000)


class AnalyzedFoodItem(BaseModel):
    """A single food item estimated by the model.

    Mirrors ``FoodItemCreate`` so results can be submitted to ``POST /meal`` as-is.
    Macro values are quantized to two decimal places, since the model may return
    more precision than the database column accepts.
    """

    name: str = Field(min_length=1, max_length=255)
    calories: int = Field(ge=0)
    protein: Decimal = Field(ge=0, le=_MAX_MACRO)
    carbs: Decimal = Field(ge=0, le=_MAX_MACRO)
    fat: Decimal = Field(ge=0, le=_MAX_MACRO)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("protein", "carbs", "fat")
    @classmethod
    def _quantize(cls, value: Decimal) -> Decimal:
        return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


class NutritionAnalysis(BaseModel):
    """Structured nutrition estimate for a meal description."""

    food_items: list[AnalyzedFoodItem]
    confidence: float | None = Field(default=None, ge=0, le=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_calories(self) -> int:
        return sum(item.calories for item in self.food_items)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_protein(self) -> Decimal:
        return sum((item.protein for item in self.food_items), Decimal(0))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_carbs(self) -> Decimal:
        return sum((item.carbs for item in self.food_items), Decimal(0))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_fat(self) -> Decimal:
        return sum((item.fat for item in self.food_items), Decimal(0))
