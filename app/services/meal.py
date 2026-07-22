"""Meal service: logging, listing, and deleting a user's meals."""

import logging
import uuid

from app.models.meal import FoodItem, Meal
from app.repositories.meal import MealRepository
from app.schemas.meal import MealCreate
from app.services.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class MealNotFoundError(ResourceNotFoundError):
    """Raised when a meal is missing or not owned by the caller."""

    detail = "meal not found"


class MealService:
    """Business logic for meal management. All operations are user-scoped."""

    def __init__(self, meal_repository: MealRepository) -> None:
        self._meals = meal_repository

    async def create_meal(self, user_id: uuid.UUID, data: MealCreate) -> Meal:
        """Create a meal and its food items atomically."""
        meal = Meal(
            user_id=user_id,
            meal_type=data.meal_type,
            meal_time=data.meal_time,
            image_url=data.image_url,
            food_items=[
                FoodItem(
                    name=item.name,
                    calories=item.calories,
                    protein=item.protein,
                    carbs=item.carbs,
                    fat=item.fat,
                    confidence=item.confidence,
                )
                for item in data.food_items
            ],
        )
        created = await self._meals.create(meal)
        logger.info("Created meal %s for user %s", created.id, user_id)
        return created

    async def list_meals(
        self,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> list[Meal]:
        """Return the user's meals, newest first."""
        return await self._meals.list_by_user(user_id, limit, offset)

    async def delete_meal(self, user_id: uuid.UUID, meal_id: uuid.UUID) -> None:
        """Delete a meal owned by ``user_id``.

        Raises :class:`MealNotFoundError` when the meal is missing *or* owned by
        someone else, so callers cannot probe for foreign meal ids.
        """
        meal = await self._meals.get_by_id(meal_id)
        if meal is None or meal.user_id != user_id:
            raise MealNotFoundError()
        await self._meals.delete(meal)
        logger.info("Deleted meal %s for user %s", meal_id, user_id)
