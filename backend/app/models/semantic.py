"""
models/semantic.py — SemanticEvent and MeetingTopic ORM models.

SemanticEventType encodes the full 17-type taxonomy.

ESCALATION INVARIANTS (enforced in semantic_engine.py):
  SUGGESTION → DECISION_CANDIDATE requires agreement signal
  OPINION    → DECISION_CANDIDATE requires agreement signal
  DECISION_CANDIDATE → DECISION_CONFIRMED requires explicit acceptance + no DISAGREEMENT
  Any → DECISION_CONFIRMED requires no unresolved Contradiction on same topic

INVARIANT: evidence_ids must NEVER be empty. Raise ValueError if empty.
"""
import uuid
from enum import Enum

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SemanticEventType(str, Enum):
    # Discourse
    IDEA = "IDEA"
    SUGGESTION = "SUGGESTION"
    OPINION = "OPINION"
    DISCUSSION = "DISCUSSION"
    # Decision track
    DECISION_CANDIDATE = "DECISION_CANDIDATE"
    DECISION_CONFIRMED = "DECISION_CONFIRMED"
    # Action track
    COMMITMENT = "COMMITMENT"
    ACTION_ITEM = "ACTION_ITEM"
    # Interrogative
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"
    # Risk track
    BLOCKER = "BLOCKER"
    RISK = "RISK"
    DEADLINE = "DEADLINE"
    STATUS_UPDATE = "STATUS_UPDATE"
    # Conflict track
    DISAGREEMENT = "DISAGREEMENT"
    CONTRADICTION = "CONTRADICTION"
    # Human marks (highest trust, source=HUMAN)
    USER_MARK = "USER_MARK"


class ReviewState(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    UNCERTAIN = "UNCERTAIN"


class SemanticEvent(Base):
    """
    A meaningful event extracted from the meeting transcript.

    evidence_ids: JSON list of Evidence UUIDs. MUST be non-empty.
    extraction_stage: which ProcessingRun stage produced this event.
    confidence: field-level extraction confidence.
    """
    __tablename__ = "semantic_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extraction_stage: Mapped[str] = mapped_column(String(50), nullable=False, default="SEMANTIC")
    review_state: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReviewState.PENDING
    )


class MeetingTopic(Base):
    """A discussion topic within a meeting, with time bounds."""
    __tablename__ = "meeting_topics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
