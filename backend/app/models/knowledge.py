"""
models/knowledge.py — KnowledgeItem and TerminologyEntry ORM models.

INVARIANT: KnowledgeItem.verified=True requires EITHER:
  - verification_source = HUMAN (user confirmed)
  - OR system confidence >= settings.min_auto_accept_confidence

verification_source = INFERRED is NEVER sufficient to set verified=True.
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # FACT|DECISION|TERMINOLOGY|PERSON|PROJECT|ACRONYM|PATTERN
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_meeting_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_source: Mapped[str] = mapped_column(String(20), nullable=False, default="INFERRED")  # HUMAN|SYSTEM|INFERRED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TerminologyEntry(Base):
    __tablename__ = "terminology_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    term: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    canonical_meaning: Mapped[str] = mapped_column(Text, nullable=False)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_meeting_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
