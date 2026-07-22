"""Meal and FoodItem ORM models."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class MealType(StrEnum):
    """Allowed meal categories."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class Meal(Base):
    """A logged meal belonging to a user, composed of one or more food items."""

    __tablename__ = "meals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    meal_type: Mapped[MealType] = mapped_column(
        SAEnum(MealType, native_enum=False, length=20),
        nullable=False,
    )
    meal_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    food_items: Mapped[list["FoodItem"]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
    )
    user: Mapped["User"] = relationship(back_populates="meals")


class FoodItem(Base):
    """A single food item with nutrition values within a meal."""

    __tablename__ = "food_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    meal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    calories: Mapped[int] = mapped_column(Integer, nullable=False)
    protein: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    carbs: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fat: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    meal: Mapped["Meal"] = relationship(back_populates="food_items")
