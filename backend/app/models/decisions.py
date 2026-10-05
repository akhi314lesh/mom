"""
models/decisions.py — Decision ORM model.

Decisions are derived from SemanticEvents of type DECISION_CANDIDATE/CONFIRMED.

INVARIANT: evidence_ids must NEVER be empty.
INVARIANT: status=CONFIRMED requires no unresolved Contradiction on same topic.
INVARIANT: The system prefers UNRESOLVED over inventing a resolution.
"""
import uuid

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DecisionStatus(str):
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    UNRESOLVED = "UNRESOLVED"
    OVERRIDDEN = "OVERRIDDEN"


class Decision(Base):
    """
    A confirmed or candidate decision from the meeting.

    status progression:
      CANDIDATE → CONFIRMED (with consensus + no DISAGREEMENT)
      CANDIDATE → UNRESOLVED (if contradiction detected)
      CONFIRMED → OVERRIDDEN (by later meeting decision)
    """
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    semantic_event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("semantic_events.id", ondelete="RESTRICT"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CANDIDATE")
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    review_state: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    overridden_by_meeting_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
