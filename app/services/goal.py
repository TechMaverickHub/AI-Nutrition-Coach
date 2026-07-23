"""Goal service: reading and upserting a user's daily nutrition targets."""

import logging
import uuid

from sqlalchemy.exc import IntegrityError

from app.models.goal import Goal
from app.repositories.goal import GoalRepository
from app.schemas.goal import GoalUpsert
from app.services.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class GoalNotFoundError(ResourceNotFoundError):
    """Raised when the user has not configured a goal."""

    detail = "goal not found"


class GoalService:
    """Business logic for goals. One goal per user, enforced by a unique index."""

    def __init__(self, goal_repository: GoalRepository) -> None:
        self._goals = goal_repository

    async def get_goal(self, user_id: uuid.UUID) -> Goal:
        """Return the user's goal, or raise :class:`GoalNotFoundError`."""
        goal = await self._goals.get_by_user(user_id)
        if goal is None:
            raise GoalNotFoundError()
        return goal

    async def set_goal(self, user_id: uuid.UUID, data: GoalUpsert) -> Goal:
        """Create the user's goal, or replace it if one already exists."""
        existing = await self._goals.get_by_user(user_id)
        if existing is not None:
            return await self._apply(existing, data)

        goal = Goal(user_id=user_id, **data.model_dump())
        try:
            created = await self._goals.create(goal)
        except IntegrityError:
            # Concurrent create lost the unique-constraint race; fall back to an
            # update so PUT stays idempotent.
            await self._goals.rollback()
            current = await self._goals.get_by_user(user_id)
            if current is None:
                raise
            return await self._apply(current, data)

        logger.info("Created goal for user %s", user_id)
        return created

    async def _apply(self, goal: Goal, data: GoalUpsert) -> Goal:
        goal.daily_calories = data.daily_calories
        goal.protein_goal = data.protein_goal
        goal.carb_goal = data.carb_goal
        goal.fat_goal = data.fat_goal
        updated = await self._goals.update(goal)
        logger.info("Updated goal for user %s", goal.user_id)
        return updated
