"""api/evidence.py — Evidence retrieval."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.evidence import Evidence

router = APIRouter()

@router.get("/{meeting_id}", summary="Get all evidence for a meeting")
async def get_evidence(meeting_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Evidence).where(Evidence.meeting_id == meeting_id))
    records = result.scalars().all()
    return [
        {
            "id": e.id, "source_type": e.source_type, "source_modality": e.source_modality,
            "timestamp_ms": e.timestamp_ms, "raw_text": e.raw_text,
            "confidence": e.confidence, "segment_id": e.segment_id,
        }
        for e in records
    ]

@router.get("/{meeting_id}/item/{evidence_id}", summary="Get a single evidence record")
async def get_evidence_item(meeting_id: str, evidence_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id, Evidence.meeting_id == meeting_id))
    e = result.scalar_one_or_none()
    if not e:
        return {"error": "Evidence not found"}
    return {
        "id": e.id,
        "meeting_id": e.meeting_id,
        "source_type": e.source_type,
        "source_modality": e.source_modality,
        "raw_text": e.raw_text,
        "confidence": e.confidence,
        "timestamp_ms": e.timestamp_ms,
        "is_immutable": e.is_immutable,
        "segment_id": e.segment_id,
        "user_mark_id": e.user_mark_id,
    }
