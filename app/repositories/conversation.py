"""Conversation repository — database access for conversations and messages."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message


class ConversationRepository:
    """Persistence for :class:`Conversation` and its :class:`Message` children.

    Reads eagerly load ``messages``; lazy loading is not usable under asyncio.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, conversation: Conversation) -> Conversation:
        self._session.add(conversation)
        await self._session.commit()
        await self._session.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def add_messages(self, *messages: Message) -> None:
        """Persist new messages and refresh the parent conversation's timestamp."""
        self._session.add_all(messages)
        await self._session.commit()

    async def delete(self, conversation: Conversation) -> None:
        await self._session.delete(conversation)
        await self._session.commit()
