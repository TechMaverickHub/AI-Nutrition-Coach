"""Goal DTOs."""

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Upper bound matches the Numeric(6, 2) columns these values are stored in.
_MAX_MACRO = Decimal("9999.99")
_CENTS = Decimal("0.01")


class GoalUpsert(BaseModel):
    """Payload for creating or replacing the current user's goal."""

    daily_calories: int = Field(ge=1, le=20000)
    protein_goal: Decimal = Field(ge=0, le=_MAX_MACRO)
    carb_goal: Decimal = Field(ge=0, le=_MAX_MACRO)
    fat_goal: Decimal = Field(ge=0, le=_MAX_MACRO)

    @field_validator("protein_goal", "carb_goal", "fat_goal")
    @classmethod
    def _quantize(cls, value: Decimal) -> Decimal:
        """Clamp precision to what the database column stores."""
        return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


class GoalRead(BaseModel):
    """A user's daily nutrition targets."""

    model_config = ConfigDict(from_attributes=True)

    daily_calories: int
    protein_goal: Decimal
    carb_goal: Decimal
    fat_goal: Decimal
