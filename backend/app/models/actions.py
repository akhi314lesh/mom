"""
models/actions.py — ActionItem ORM model.

ActionItems are CROSS-MEETING entities. They survive beyond their originating meeting.
originating_meeting_id is set at creation and never changes.
last_updated_meeting_id tracks the most recent meeting that updated this item.

Field-level confidence: confidence, owner_confidence, deadline_confidence
are separate scores — the task may be clear (high confidence) while the
owner may be ambiguous (low owner_confidence).
"""
import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ActionItemStatus(str):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class ActionItemPriority(str):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionItem(Base):
    """
    A task extracted from a meeting.

    Cross-meeting: originating_meeting_id never changes after creation.
    Meeting continuity updates status and last_updated_meeting_id.

    evidence_ids: MUST be non-empty (data integrity invariant).
    owner_confidence: field-level confidence for who owns this task.
    deadline_confidence: field-level confidence for the deadline.
    """
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    originating_meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="RESTRICT"), nullable=False
    )
    originating_timestamp_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    owner_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    review_state: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    last_updated_meeting_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
