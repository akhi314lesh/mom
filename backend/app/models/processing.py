"""
models/processing.py — ProcessingRun and ProcessingLedger ORM models.

ProcessingRun tracks each pipeline stage execution.

INVARIANT: input_hash enables idempotency. Before re-running a stage,
compute SHA-256 of inputs. If hash matches stored value, skip.

INVARIANT: depends_on_stages enables dependency-aware invalidation.
When a correction occurs at stage X, only stages in descendants(X) are INVALIDATED.
Upstream stages (ancestors of X) remain COMPLETE.

Stage dependency order: ASR → DIARIZATION → IDENTITY → SEMANTIC → VALIDATION → WORLD_MODEL → ARTIFACTS
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

# Stage dependency graph — used by agent_orchestrator.py
STAGE_DEPENDENCIES: dict[str, list[str]] = {
    "ASR": [],
    "DIARIZATION": ["ASR"],
    "IDENTITY": ["DIARIZATION"],
    "SEMANTIC": ["IDENTITY"],
    "VALIDATION": ["SEMANTIC"],
    "WORLD_MODEL": ["VALIDATION"],
    "ARTIFACTS": ["WORLD_MODEL"],
}


def get_downstream_stages(stage: str) -> list[str]:
    """Return all stages that depend (directly or transitively) on the given stage."""
    downstream = []
    for s, deps in STAGE_DEPENDENCIES.items():
        if stage in deps:
            downstream.append(s)
            downstream.extend(get_downstream_stages(s))
    return list(set(downstream))


class ProcessingRun(Base):
    __tablename__ = "processing_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")  # QUEUED|RUNNING|COMPLETE|FAILED|SKIPPED|INVALIDATED
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(200), nullable=True)
    adapter_used: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimate_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    input_evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    output_evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256 hex
    depends_on_stages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessingLedger(Base):
    """Per-meeting processing cost + latency ledger. One row per meeting."""
    __tablename__ = "processing_ledgers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_cost_estimate_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stages_run: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    stages_skipped: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
