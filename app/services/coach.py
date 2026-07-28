"""Coach service: personalized chat with persisted conversation history."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from app.models.conversation import Conversation, Message, MessageRole
from app.repositories.conversation import ConversationRepository
from app.schemas.dashboard import DashboardRead
from app.services.ai.errors import AIUnavailableError
from app.services.ai.prompts import load_prompt
from app.services.dashboard import DashboardService
from app.services.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)

# Most recent messages replayed to the model, to bound token cost.
_HISTORY_LIMIT = 20
_TITLE_MAX = 60


class ConversationNotFoundError(ResourceNotFoundError):
    """Raised when a conversation is missing or not owned by the caller."""

    detail = "conversation not found"


class CoachService:
    """Runs coach chat turns and manages conversation history, per user."""

    def __init__(
        self,
        model: Runnable[Any, Any],
        conversation_repository: ConversationRepository,
        dashboard_service: DashboardService,
    ) -> None:
        self._model = model
        self._conversations = conversation_repository
        self._dashboard = dashboard_service

    async def chat(
        self,
        user_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None,
    ) -> tuple[uuid.UUID, str]:
        """Handle one chat turn; returns ``(conversation_id, reply)``."""
        conversation = await self._resolve_conversation(user_id, conversation_id, message)

        context = await self._build_context(user_id)
        history = conversation.messages if conversation_id is not None else []
        lc_messages = self._build_messages(context, history, message)

        reply = await self._invoke(lc_messages)

        conversation.updated_at = datetime.now(UTC)
        await self._conversations.add_messages(
            Message(conversation_id=conversation.id, role=MessageRole.USER, content=message),
            Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=reply,
            ),
        )
        logger.info("Coach reply for user %s conversation %s", user_id, conversation.id)
        return conversation.id, reply

    async def list_conversations(self, user_id: uuid.UUID) -> list[Conversation]:
        return await self._conversations.list_by_user(user_id)

    async def get_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError()
        return conversation

    async def delete_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> None:
        conversation = await self.get_conversation(user_id, conversation_id)
        await self._conversations.delete(conversation)

    # -- internals ---------------------------------------------------------

    async def _resolve_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID | None, message: str
    ) -> Conversation:
        if conversation_id is None:
            conversation = Conversation(user_id=user_id, title=message[:_TITLE_MAX])
            return await self._conversations.create(conversation)
        return await self.get_conversation(user_id, conversation_id)

    def _build_messages(
        self, context: str, history: list[Message], new_message: str
    ) -> list[BaseMessage]:
        system_text = f"{load_prompt('coach_system')}\n\n{context}"
        messages: list[BaseMessage] = [SystemMessage(system_text)]
        for stored in history[-_HISTORY_LIMIT:]:
            if stored.role == MessageRole.USER:
                messages.append(HumanMessage(stored.content))
            else:
                messages.append(AIMessage(stored.content))
        messages.append(HumanMessage(new_message))
        return messages

    async def _invoke(self, messages: list[BaseMessage]) -> str:
        try:
            result = await self._model.ainvoke(messages)
        except Exception as exc:  # noqa: BLE001 - upstream/provider failure
            logger.error("Coach model request failed: %s", exc)
            raise AIUnavailableError() from exc
        content = getattr(result, "content", result)
        return content if isinstance(content, str) else str(content)

    async def _build_context(self, user_id: uuid.UUID) -> str:
        summary = await self._dashboard.get_summary(user_id)
        return self._format_context(summary)

    @staticmethod
    def _format_context(summary: DashboardRead) -> str:
        lines = [f"User's context for {summary.date.isoformat()}:"]
        if summary.goal is None:
            lines.append("- The user has not set a daily nutrition goal.")
        else:
            g = summary.goal
            lines.append(
                f"- Goal: {g.daily_calories} kcal, protein {g.protein_goal}g, "
                f"carbs {g.carb_goal}g, fat {g.fat_goal}g."
            )
        if summary.meal_count == 0:
            lines.append("- Nothing logged yet today.")
        else:
            t = summary.totals
            lines.append(
                f"- Consumed ({summary.meal_count} meals): {t.calories} kcal, "
                f"protein {t.protein}g, carbs {t.carbs}g, fat {t.fat}g."
            )
            if summary.remaining is not None:
                r = summary.remaining
                lines.append(
                    f"- Remaining vs goal: {r.calories} kcal, protein {r.protein}g, "
                    f"carbs {r.carbs}g, fat {r.fat}g (negative means over)."
                )
        return "\n".join(lines)
