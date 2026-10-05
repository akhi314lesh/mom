"""
api/capture.py — Capture session management and Mark Moment (ADR-005, ADR-006).

Provides:
- Starting/stopping capture sessions with AudioSourceState detection
- Mark Moment endpoints (creating immutable Evidence + UserMark records)
- Graceful degradation simulation and status reporting
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.ws import manager as ws_manager
from app.capture.manager import capture_manager
from app.database import get_db
from app.models.capture import (
    AudioSourceState,
    CaptureSession,
    CaptureSource,
    CaptureSourceStatus,
    CaptureSourceType,
)
from app.models.evidence import Evidence
from app.models.marks import UserMark
from app.models.meeting import Meeting

router = APIRouter()


class StartSessionRequest(BaseModel):
    meeting_id: str
    capture_mode: str = "OVERLAY"
    enable_mic: bool = True
    enable_sys: bool = True


class CreateMarkRequest(BaseModel):
    timestamp_ms: Optional[int] = None
    event_type: str = Field(default="USER_MARK", description="USER_MARK, NOTE, DECISION, ACTION, FLAG, KEY_MOMENT")
    text: Optional[str] = None
    note: Optional[str] = None
    priority: float = 1.0


class SimulateToggleRequest(BaseModel):
    source: str = Field(..., description="'mic' or 'sys'")
    force_fail: bool = True


@router.get("/{meeting_id}/session", summary="Get active or latest capture session")
async def get_capture_session(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Fetch the active or most recent capture session with source status."""
    stmt = (
        select(CaptureSession)
        .options(selectinload(CaptureSession.sources))
        .where(CaptureSession.meeting_id == meeting_id)
        .order_by(desc(CaptureSession.started_at))
    )
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        return {
            "meeting_id": meeting_id,
            "session": None,
            "audio_source_state": AudioSourceState.NO_AUDIO.value,
            "message": "No capture session initiated yet for this meeting.",
        }

    sources_data = [
        {
            "id": s.id,
            "source_type": s.source_type,
            "status": s.status,
            "device_name": s.device_name,
            "degradation_reason": s.degradation_reason,
        }
        for s in session.sources
    ]

    return {
        "meeting_id": meeting_id,
        "session": {
            "id": session.id,
            "meeting_id": session.meeting_id,
            "capture_mode": session.capture_mode,
            "audio_source_state": session.audio_source_state,
            "audio_source_status": session.audio_source_status,
            "evidence_manifest": session.evidence_manifest,
            "is_active": session.is_active,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "sources": sources_data,
        },
    }


@router.post("/session/start", summary="Start or re-activate a capture session")
async def start_session(req: StartSessionRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Starts capture session with hardware check and graceful degradation."""
    meeting = await db.get(Meeting, req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    session = await capture_manager.start_session(
        db=db,
        meeting_id=req.meeting_id,
        capture_mode=req.capture_mode,
        enable_mic=req.enable_mic,
        enable_sys=req.enable_sys,
    )

    return {
        "status": "started",
        "session_id": session.id,
        "capture_mode": session.capture_mode,
        "audio_source_state": session.audio_source_state,
        "audio_source_status": session.audio_source_status,
        "evidence_manifest": session.evidence_manifest,
    }


@router.post("/{meeting_id}/session/stop", summary="Stop active capture session")
async def stop_session(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Stops the active capture session and advances meeting lifecycle."""
    session = await capture_manager.stop_session(db=db, meeting_id=meeting_id)
    if not session:
        return {"status": "noop", "message": "No active capture session found to stop."}

    return {
        "status": "stopped",
        "session_id": session.id,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }


@router.post("/{meeting_id}/mark", summary="Create a UserMark (Mark Moment)")
async def create_user_mark(
    meeting_id: str,
    req: CreateMarkRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Creates an immutable UserMark and corresponding Evidence record.
    ADR-005 / ADR-006 / ADR-008:
    - User marks are human-sourced (source is ALWAYS 'HUMAN').
    - Evidence records are immutable.
    - UserMark gives priority processing boost to the marked timestamp.
    """
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found")

    # Find active or latest capture session; if none exists, auto-create one
    stmt = (
        select(CaptureSession)
        .where(CaptureSession.meeting_id == meeting_id)
        .order_by(desc(CaptureSession.started_at))
    )
    result = await db.execute(stmt)
    session = result.scalars().first()

    now = datetime.now(timezone.utc)

    if not session:
        session = await capture_manager.start_session(
            db=db, meeting_id=meeting_id, capture_mode="OVERLAY", enable_mic=False, enable_sys=False
        )

    # Compute meeting relative timestamp_ms
    if req.timestamp_ms is not None:
        ts_ms = req.timestamp_ms
    elif session.started_at:
        started = session.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        delta = (now - started).total_seconds()
        ts_ms = max(0, int(delta * 1000))
    else:
        ts_ms = 0

    mark_text = req.text or req.note or ""

    user_mark = UserMark(
        id=str(uuid4()),
        meeting_id=meeting_id,
        capture_session_id=session.id,
        timestamp_ms=ts_ms,
        wall_clock_time=now,
        event_type=req.event_type.upper(),
        optional_text=mark_text,
        source="HUMAN",  # INVARIANT: never override
        processing_priority=min(1.0, max(0.5, req.priority)),
    )
    db.add(user_mark)
    await db.flush()

    # Create immutable Evidence record
    evidence_text = f"[{req.event_type.upper()}] {mark_text}" if mark_text else f"[{req.event_type.upper()}] Mark Moment"
    evidence = Evidence(
        id=str(uuid4()),
        meeting_id=meeting_id,
        user_mark_id=user_mark.id,
        source_type="USER_MARK",
        source_modality="TEXT",
        timestamp_ms=ts_ms,
        raw_text=evidence_text,
        confidence=1.0,  # Human input has 1.0 confidence
        is_immutable=True,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(user_mark)
    await db.refresh(evidence)

    # Broadcast event to meeting and overlay WebSockets
    payload = {
        "id": user_mark.id,
        "meeting_id": user_mark.meeting_id,
        "timestamp_ms": user_mark.timestamp_ms,
        "event_type": user_mark.event_type,
        "optional_text": user_mark.optional_text,
        "source": user_mark.source,
        "processing_priority": user_mark.processing_priority,
        "created_at": user_mark.created_at.isoformat() if user_mark.created_at else now.isoformat(),
        "evidence_id": evidence.id,
    }

    await ws_manager.broadcast(
        meeting_id,
        {
            "type": "USER_MARK",
            "mark": payload,
            "evidence": {
                "id": evidence.id,
                "source_type": evidence.source_type,
                "raw_text": evidence.raw_text,
                "confidence": evidence.confidence,
                "timestamp_ms": evidence.timestamp_ms,
            },
        },
    )

    return {
        "success": True,
        "mark": payload,
        "evidence_id": evidence.id,
    }


@router.get("/{meeting_id}/marks", summary="Get all UserMarks for a meeting")
async def list_user_marks(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Retrieve all user marks recorded during capture."""
    stmt = (
        select(UserMark)
        .where(UserMark.meeting_id == meeting_id)
        .order_by(UserMark.timestamp_ms.asc(), UserMark.created_at.asc())
    )
    result = await db.execute(stmt)
    marks = result.scalars().all()

    return {
        "meeting_id": meeting_id,
        "count": len(marks),
        "marks": [
            {
                "id": m.id,
                "meeting_id": m.meeting_id,
                "capture_session_id": m.capture_session_id,
                "timestamp_ms": m.timestamp_ms,
                "wall_clock_time": m.wall_clock_time.isoformat() if m.wall_clock_time else None,
                "event_type": m.event_type,
                "optional_text": m.optional_text,
                "source": m.source,
                "processing_priority": m.processing_priority,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in marks
        ],
    }


@router.post("/{meeting_id}/simulate-toggle", summary="Simulate audio source failure/recovery")
async def simulate_audio_toggle(
    meeting_id: str,
    req: SimulateToggleRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Tests graceful degradation by forcing a source into FAILED or ACTIVE state."""
    session = await capture_manager.simulate_source_toggle(
        db=db,
        meeting_id=meeting_id,
        source=req.source.lower(),
        force_fail=req.force_fail,
    )
    if not session:
        raise HTTPException(status_code=404, detail="No active capture session to toggle")

    return {
        "meeting_id": meeting_id,
        "audio_source_state": session.audio_source_state,
        "audio_source_status": session.audio_source_status,
        "evidence_manifest": session.evidence_manifest,
    }
