"""Goal repository — database access for the ``goals`` table only."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal


class GoalRepository:
    """Encapsulates persistence operations for :class:`Goal`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user(self, user_id: uuid.UUID) -> Goal | None:
        result = await self._session.execute(
            select(Goal).where(Goal.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, goal: Goal) -> Goal:
        self._session.add(goal)
        await self._session.commit()
        await self._session.refresh(goal)
        return goal

    async def update(self, goal: Goal) -> Goal:
        """Persist in-place changes to an already-tracked goal."""
        await self._session.commit()
        await self._session.refresh(goal)
        return goal

    async def rollback(self) -> None:
        await self._session.rollback()
