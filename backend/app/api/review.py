"""api/review.py — Review queue management."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.review import ReviewItem

router = APIRouter()

@router.get("/{meeting_id}", summary="Get review queue for a meeting")
async def get_review_queue(meeting_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        select(ReviewItem)
        .where(ReviewItem.meeting_id == meeting_id, ReviewItem.status == "PENDING")
        .order_by(ReviewItem.priority_score.desc())
    )
    items = result.scalars().all()
    return [{"id": r.id, "type": r.type, "question": r.question, "options": r.options, "context": r.context, "evidence_ids": r.evidence_ids, "priority_score": r.priority_score} for r in items]

@router.patch("/{meeting_id}/item/{item_id}", summary="Resolve a review item")
async def resolve_review_item(meeting_id: str, item_id: str, body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Resolve a review item.
    Applies human correction, creates immutable Evidence, invalidates downstream
    stages, marks artifacts STALE, and regenerates current DOCX artifact (ADR-008, ADR-011).
    """
    from app.pipeline.corrections import apply_human_correction

    result = await db.execute(select(ReviewItem).where(ReviewItem.id == item_id, ReviewItem.meeting_id == meeting_id))
    item = result.scalar_one_or_none()
    if not item:
        return {"error": "Review item not found"}

    old_status = item.status
    resolution = body.get("resolution") or body.get("status", "RESOLVED")
    item.status = body.get("status", "RESOLVED")
    item.resolution = resolution
    await db.commit()

    corr_res = await apply_human_correction(
        db=db,
        meeting_id=meeting_id,
        target_type="REVIEW_ITEM",
        target_id=item_id,
        field="resolution",
        old_value=old_status,
        new_value=resolution,
        origin_stage="SEMANTIC",
    )

    return {
        "id": item.id,
        "status": item.status,
        "resolution": item.resolution,
        "correction": corr_res,
    }
