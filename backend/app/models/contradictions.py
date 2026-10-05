"""
models/contradictions.py — Contradiction ORM model.

INVARIANT: The system ALWAYS prefers DECISION UNRESOLVED over silently
choosing one side of a contradiction.

Both sides are preserved in evidence. Human confirmation is required
before either side is promoted to canonical truth.
"""
import uuid
from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ContradictionType(str):
    DEADLINE = "DEADLINE"
    DECISION = "DECISION"
    OWNER = "OWNER"
    FACTUAL = "FACTUAL"
    CROSS_MEETING = "CROSS_MEETING"


class Contradiction(Base):
    """
    Detected contradiction between two semantic events or decisions.

    is_cross_meeting=True: spans multiple meetings (meeting_id may be None).
    Both event_a and event_b are preserved; neither is silently discarded.
    """
    __tablename__ = "contradictions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)
    event_a_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_b_id: Mapped[str] = mapped_column(String(36), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contradiction_type: Mapped[str] = mapped_column(String(20), nullable=False, default="FACTUAL")
    is_cross_meeting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    meeting_a_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    meeting_b_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_state: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
