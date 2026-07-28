"""Coach chat DTOs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.conversation import MessageRole


class ChatRequest(BaseModel):
    """A message to the coach. Omit ``conversation_id`` to start a new conversation."""

    message: str = Field(min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    """The coach's reply and the conversation it belongs to."""

    conversation_id: uuid.UUID
    reply: str


class MessageRead(BaseModel):
    """A persisted message."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class ConversationRead(BaseModel):
    """A conversation summary (list view)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationRead):
    """A conversation with its full message thread."""

    messages: list[MessageRead]
