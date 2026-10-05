"""api/agent_console.py — Agent state endpoint for the Agent Console UI."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.meeting import Meeting
from app.models.processing import ProcessingRun, ProcessingLedger
from app.models.review import ReviewItem
from app.models.decisions import Decision
from app.models.actions import ActionItem

router = APIRouter()


@router.get("/{meeting_id}/state", summary="Get current agent state for a meeting")
async def get_agent_state(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Returns the agent's current state, processing ledger, world model summary,
    and human attention queue. Does NOT expose chain-of-thought.
    Exposes: system state, evidence metrics, world model facts, review queue.
    """
    # Meeting
    m_result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = m_result.scalar_one_or_none()
    if not meeting:
        return {"error": "Meeting not found"}

    # Processing runs
    runs_result = await db.execute(
        select(ProcessingRun).where(ProcessingRun.meeting_id == meeting_id)
    )
    runs = runs_result.scalars().all()

    # Ledger
    ledger_result = await db.execute(
        select(ProcessingLedger).where(ProcessingLedger.meeting_id == meeting_id)
    )
    ledger = ledger_result.scalar_one_or_none()

    # Review items (pending)
    review_result = await db.execute(
        select(ReviewItem)
        .where(ReviewItem.meeting_id == meeting_id, ReviewItem.status == "PENDING")
        .order_by(ReviewItem.priority_score.desc())
    )
    pending_reviews = review_result.scalars().all()

    # World model counts
    decisions_result = await db.execute(
        select(Decision).where(Decision.meeting_id == meeting_id)
    )
    decisions = decisions_result.scalars().all()

    actions_result = await db.execute(
        select(ActionItem).where(ActionItem.originating_meeting_id == meeting_id)
    )
    actions = actions_result.scalars().all()

    current_run = next((r for r in reversed(runs) if r.status == "RUNNING"), None)
    stages_run = [r.stage for r in runs if r.status == "COMPLETE"]
    stages_skipped = [r.stage for r in runs if r.status == "SKIPPED"]

    return {
        "current_meeting": {
            "id": meeting.id,
            "title": meeting.title,
            "lifecycle_status": meeting.lifecycle_status,
            "processing_status": meeting.processing_status,
            "capture_mode": meeting.capture_mode,
            "privacy_mode": meeting.privacy_mode,
        },
        "agent_state": {
            "current_state": meeting.processing_status,
            "current_stage": current_run.stage if current_run else "IDLE",
            "stages_run": stages_run,
            "stages_skipped": stages_skipped,
            "total_runs": len(runs),
        },
        "processing_ledger": {
            "total_cost_usd": ledger.total_cost_estimate_usd if ledger else 0.0,
            "total_latency_ms": ledger.total_latency_ms if ledger else 0,
            "stages_run": ledger.stages_run if ledger else [],
            "stages_skipped": ledger.stages_skipped if ledger else [],
        },
        "world_model": {
            "decisions_total": len(decisions),
            "decisions_confirmed": sum(1 for d in decisions if d.status == "CONFIRMED"),
            "decisions_candidate": sum(1 for d in decisions if d.status == "CANDIDATE"),
            "decisions_unresolved": sum(1 for d in decisions if d.status == "UNRESOLVED"),
            "action_items_total": len(actions),
            "action_items_pending": sum(1 for a in actions if a.status == "PENDING"),
        },
        "human_attention": {
            "pending_review_count": len(pending_reviews),
            "top_items": [
                {
                    "id": r.id,
                    "type": r.type,
                    "question": r.question,
                    "priority_score": r.priority_score,
                }
                for r in pending_reviews[:5]
            ],
        },
        "quality_metrics": meeting.quality_metrics or {},
    }
