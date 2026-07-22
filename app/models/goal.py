"""Goal ORM model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Goal(Base):
    """A user's daily nutrition targets (one active goal per user)."""

    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    daily_calories: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_goal: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    carb_goal: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fat_goal: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    user: Mapped["User"] = relationship(back_populates="goal")
