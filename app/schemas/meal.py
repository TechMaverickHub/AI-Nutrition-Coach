"""Meal and food item DTOs."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.meal import MealType


class FoodItemCreate(BaseModel):
    """A single food item supplied when logging a meal."""

    name: str = Field(min_length=1, max_length=255)
    calories: int = Field(ge=0)
    protein: Decimal = Field(ge=0, max_digits=6, decimal_places=2)
    carbs: Decimal = Field(ge=0, max_digits=6, decimal_places=2)
    fat: Decimal = Field(ge=0, max_digits=6, decimal_places=2)
    confidence: float | None = Field(default=None, ge=0, le=1)


class FoodItemRead(BaseModel):
    """A persisted food item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    calories: int
    protein: Decimal
    carbs: Decimal
    fat: Decimal
    confidence: float | None


class MealCreate(BaseModel):
    """Payload for logging a meal together with its food items."""

    meal_type: MealType
    meal_time: datetime
    image_url: str | None = Field(default=None, max_length=1024)
    food_items: list[FoodItemCreate] = Field(min_length=1)


class MealRead(BaseModel):
    """A persisted meal with its items and derived nutrition totals."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meal_type: MealType
    meal_time: datetime
    image_url: str | None
    created_at: datetime
    food_items: list[FoodItemRead]

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
