"""Meal repository — database access for meals and their food items."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meal import FoodItem, Meal


@dataclass(frozen=True)
class NutritionAggregate:
    """Summed nutrition values and meal count for a period."""

    calories: int
    protein: Decimal
    carbs: Decimal
    fat: Decimal
    meal_count: int


class MealRepository:
    """Encapsulates all persistence operations for :class:`Meal`.

    Every read eagerly loads ``food_items``; lazy loading is not usable under
    asyncio once the awaiting context has moved on.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, meal: Meal) -> Meal:
        self._session.add(meal)
        await self._session.commit()
        return meal

    async def get_by_id(self, meal_id: uuid.UUID) -> Meal | None:
        result = await self._session.execute(
            select(Meal)
            .options(selectinload(Meal.food_items))
            .where(Meal.id == meal_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> list[Meal]:
        result = await self._session.execute(
            select(Meal)
            .options(selectinload(Meal.food_items))
            .where(Meal.user_id == user_id)
            .order_by(Meal.meal_time.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, meal: Meal) -> None:
        await self._session.delete(meal)
        await self._session.commit()

    async def aggregate_for_period(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> NutritionAggregate:
        """Sum nutrition across the user's meals in ``[start, end)``.

        Aggregation happens in SQL. ``SUM`` over an empty set yields NULL, so each
        total is COALESCEd to 0 and an empty period returns zeros.
        """
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(FoodItem.calories), 0).label("calories"),
                func.coalesce(func.sum(FoodItem.protein), 0).label("protein"),
                func.coalesce(func.sum(FoodItem.carbs), 0).label("carbs"),
                func.coalesce(func.sum(FoodItem.fat), 0).label("fat"),
                func.count(distinct(Meal.id)).label("meal_count"),
            )
            .select_from(Meal)
            .outerjoin(FoodItem, FoodItem.meal_id == Meal.id)
            .where(
                Meal.user_id == user_id,
                Meal.meal_time >= start,
                Meal.meal_time < end,
            )
        )
        row = result.one()
        return NutritionAggregate(
            calories=int(row.calories),
            protein=Decimal(row.protein),
            carbs=Decimal(row.carbs),
            fat=Decimal(row.fat),
            meal_count=int(row.meal_count),
        )
