"""AI coach routes. Scoped to the authenticated user."""

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import get_coach_service, get_current_user
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.coach import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationRead,
)
from app.services.coach import CoachService

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
) -> ChatResponse:
    conversation_id, reply = await service.chat(
        current_user.id, data.message, data.conversation_id
    )
    return ChatResponse(conversation_id=conversation_id, reply=reply)


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
) -> list[Conversation]:
    return await service.list_conversations(current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
) -> Conversation:
    return await service.get_conversation(current_user.id, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: CoachService = Depends(get_coach_service),
) -> None:
    await service.delete_conversation(current_user.id, conversation_id)
