"""api/transcript.py — Transcript view and editing."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.transcript import TranscriptSegment

router = APIRouter()

@router.get("/{meeting_id}", summary="Get transcript for a meeting")
async def get_transcript(meeting_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.start_ms)
    )
    segments = result.scalars().all()
    return [
        {
            "id": s.id, "speaker_id": s.speaker_id,
            "start_ms": s.start_ms, "end_ms": s.end_ms,
            "text": s.text, "language": s.language,
            "asr_confidence": s.asr_confidence,
            "is_edited": s.is_edited, "source_modality": s.source_modality,
        }
        for s in segments
    ]

@router.patch("/{meeting_id}/segment/{segment_id}", summary="Edit a transcript segment")
async def edit_segment(meeting_id: str, segment_id: str, body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Edit transcript text. Sets is_edited=True, edited_by=HUMAN.
    Phase 2: also creates Evidence{HUMAN_CORRECTION} and marks artifacts STALE.
    """
    result = await db.execute(select(TranscriptSegment).where(TranscriptSegment.id == segment_id, TranscriptSegment.meeting_id == meeting_id))
    segment = result.scalar_one_or_none()
    if not segment:
        return {"error": "Segment not found"}
    if "text" in body:
        segment.text = body["text"]
        segment.is_edited = True
        segment.edited_by = "HUMAN"
    await db.commit()
    return {"id": segment.id, "text": segment.text, "is_edited": segment.is_edited}
