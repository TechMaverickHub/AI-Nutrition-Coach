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
