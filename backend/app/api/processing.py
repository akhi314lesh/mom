"""api/processing.py — Pipeline trigger and status."""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.meeting import Meeting, ProcessingStatus

router = APIRouter()

@router.post("/{meeting_id}/run", summary="Trigger pipeline processing for a meeting")
async def run_pipeline(meeting_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> dict:
    """Runs progressive pipeline stages through the orchestrator."""
    from app.pipeline.orchestrator import process_meeting_pipeline

    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        return {"error": "Meeting not found"}

    meeting.processing_status = ProcessingStatus.QUEUED
    await db.commit()

    background_tasks.add_task(process_meeting_pipeline, meeting_id)
    return {
        "meeting_id": meeting_id,
        "status": "queued",
        "message": "Pipeline run initiated.",
    }

@router.get("/{meeting_id}/status", summary="Get processing status")
async def get_processing_status(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        return {"error": "Meeting not found"}
    return {"meeting_id": meeting_id, "processing_status": meeting.processing_status, "lifecycle_status": meeting.lifecycle_status}
