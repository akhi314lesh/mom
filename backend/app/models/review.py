"""
models/review.py — ReviewItem ORM model.

priority_score = importance × uncertainty × impact
Items with priority_score < 0.1 are not surfaced to the user.

INVARIANT: Never block artifact generation on unresolved review items.
The user can always "Leave unresolved" and the fact is marked uncertain.
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ReviewItemType(str):
    SPEAKER_IDENTITY = "SPEAKER_IDENTITY"
    AMBIGUOUS_DEADLINE = "AMBIGUOUS_DEADLINE"
    UNCERTAIN_OWNER = "UNCERTAIN_OWNER"
    CONTRADICTORY_DECISION = "CONTRADICTORY_DECISION"
    UNCLEAR_ACTION = "UNCLEAR_ACTION"
    AMBIGUOUS_METADATA = "AMBIGUOUS_METADATA"
    LOW_CONFIDENCE_DECISION = "LOW_CONFIDENCE_DECISION"
    CROSS_MEETING_CONTRADICTION = "CROSS_MEETING_CONTRADICTION"
    DISAGREEMENT = "DISAGREEMENT"


class ReviewItem(Base):
    __tablename__ = "review_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    context: Mapped[str] = mapped_column(Text, nullable=False, default="")  # evidence + rationale; NOT chain-of-thought
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")  # PENDING|RESOLVED|SKIPPED|DEFERRED
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
