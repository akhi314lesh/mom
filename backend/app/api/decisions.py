"""api/decisions.py — Decisions CRUD."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.decisions import Decision

router = APIRouter()

@router.get("/meeting/{meeting_id}", summary="List decisions for a meeting")
async def list_decisions(meeting_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Decision).where(Decision.meeting_id == meeting_id))
    return [{"id": d.id, "text": d.text, "status": d.status, "confidence": d.confidence, "review_state": d.review_state, "evidence_ids": d.evidence_ids} for d in result.scalars().all()]

@router.patch("/{decision_id}", summary="Update a decision with human correction tracking")
async def update_decision(decision_id: str, body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from app.pipeline.corrections import apply_human_correction

    result = await db.execute(select(Decision).where(Decision.id == decision_id))
    d = result.scalar_one_or_none()
    if not d:
        return {"error": "Decision not found"}

    corrections_applied = []
    for field in ("status", "review_state", "text"):
        if field in body and getattr(d, field) != body[field]:
            old_val = getattr(d, field)
            new_val = body[field]
            setattr(d, field, new_val)
            corrections_applied.append((field, old_val, new_val))

    await db.commit()

    for field, old_val, new_val in corrections_applied:
        await apply_human_correction(
            db=db,
            meeting_id=d.meeting_id,
            target_type="DECISION",
            target_id=decision_id,
            field=field,
            old_value=old_val,
            new_value=new_val,
            origin_stage="SEMANTIC",
        )

    return {"id": d.id, "status": d.status, "text": d.text, "review_state": d.review_state}
