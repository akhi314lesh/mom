"""
api/contradictions.py — Contradiction management and arbitration endpoints.

Provides:
- Contradiction querying with evidence grounding
- Manual and automated contradiction detection triggering
- Streaming live utterance ingestion
- Human arbitration resolution flow (creating immutable HUMAN_CORRECTION evidence)
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.contradictions import Contradiction
from app.models.decisions import Decision, DecisionStatus
from app.models.evidence import Evidence
from app.models.meeting import Meeting
from app.models.semantic import SemanticEvent
from app.pipeline.contradictions import contradiction_detector
from app.pipeline.live_processor import live_processor

router = APIRouter()


class ResolveContradictionRequest(BaseModel):
    resolution: str = Field(..., description="Arbitrated resolution statement")
    chosen_side: Optional[str] = Field(None, description="'A', 'B', or custom note")
    author: Optional[str] = Field("Human Arbiter", description="Name/role of reviewer")


class LiveUtteranceRequest(BaseModel):
    text: str = Field(..., description="Spoken text transcript chunk")
    start_ms: int = Field(0, description="Meeting relative start millisecond")
    end_ms: int = Field(5000, description="Meeting relative end millisecond")
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = "Speaker"
    confidence: float = 0.92


@router.get("/meeting/{meeting_id}", summary="List all contradictions for a meeting")
async def list_meeting_contradictions(
    meeting_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Retrieve all detected contradictions with evidence references."""
    stmt = select(Contradiction).where(Contradiction.meeting_id == meeting_id)
    result = await db.execute(stmt)
    contradictions = result.scalars().all()

    # Preload referenced event text
    results = []
    for c in contradictions:
        # Check if event A is a decision or semantic event
        dec_a = await db.get(Decision, c.event_a_id)
        sem_a = await db.get(SemanticEvent, c.event_a_id) if not dec_a else None
        text_a = dec_a.text if dec_a else (sem_a.text if sem_a else "Claim A")

        dec_b = await db.get(Decision, c.event_b_id)
        sem_b = await db.get(SemanticEvent, c.event_b_id) if not dec_b else None
        text_b = dec_b.text if dec_b else (sem_b.text if sem_b else "Claim B")

        results.append(
            {
                "id": c.id,
                "meeting_id": c.meeting_id,
                "contradiction_type": c.contradiction_type,
                "description": c.description,
                "event_a_id": c.event_a_id,
                "event_a_text": text_a,
                "event_b_id": c.event_b_id,
                "event_b_text": text_b,
                "is_cross_meeting": c.is_cross_meeting,
                "review_state": c.review_state,
                "confidence": c.confidence,
            }
        )

    return {
        "meeting_id": meeting_id,
        "count": len(results),
        "contradictions": results,
    }


@router.post("/{meeting_id}/detect", summary="Trigger contradiction detection")
async def trigger_contradiction_detection(
    meeting_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Runs within-meeting and cross-meeting contradiction detection algorithms."""
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    detected = await contradiction_detector.detect_within_meeting(db=db, meeting_id=meeting_id)
    cross_detected = await contradiction_detector.detect_cross_meeting(
        db=db, current_meeting_id=meeting_id
    )

    all_detected = detected + cross_detected

    return {
        "status": "success",
        "meeting_id": meeting_id,
        "detected_count": len(all_detected),
        "contradictions": [
            {
                "id": c.id,
                "type": c.contradiction_type,
                "description": c.description,
                "review_state": c.review_state,
            }
            for c in all_detected
        ],
    }


@router.post("/{meeting_id}/live-chunk", summary="Ingest live spoken utterance")
async def ingest_live_utterance(
    meeting_id: str,
    req: LiveUtteranceRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Processes incoming speech chunks in real time during live capture."""
    result = await live_processor.process_utterance(
        db=db,
        meeting_id=meeting_id,
        text=req.text,
        start_ms=req.start_ms,
        end_ms=req.end_ms,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        confidence=req.confidence,
    )
    return result


@router.patch("/{contradiction_id}/resolve", summary="Resolve a contradiction with human arbitration")
async def resolve_contradiction(
    contradiction_id: str,
    req: ResolveContradictionRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Arbitrate and resolve a contradiction.
    Enforces ADR-008: creates immutable Evidence with source_type='HUMAN_CORRECTION'.
    Enforces ADR-011: marks affected artifacts STALE and regenerates DOCX.
    """
    con = await contradiction_detector.resolve_contradiction(
        db=db,
        contradiction_id=contradiction_id,
        resolution=req.resolution,
        chosen_side=req.chosen_side,
        author=req.author or "Human Arbiter",
    )
    if not con:
        raise HTTPException(status_code=404, detail="Contradiction not found")

    return {
        "status": "resolved",
        "contradiction_id": con.id,
        "review_state": con.review_state,
        "resolution": req.resolution,
    }
