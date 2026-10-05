"""api/artifacts.py — DOCX/PDF download endpoints."""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.artifacts import Artifact, ArtifactStatus

router = APIRouter()

@router.get("/meeting/{meeting_id}", summary="List artifacts for a meeting")
async def list_artifacts(meeting_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Artifact).where(Artifact.meeting_id == meeting_id))
    return [{"id": a.id, "type": a.type, "status": a.status, "path": a.path, "file_size_bytes": a.file_size_bytes, "generated_at": a.generated_at.isoformat(), "stale_reason": a.stale_reason} for a in result.scalars().all()]

@router.get("/{artifact_id}/download", summary="Download an artifact file")
async def download_artifact(artifact_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(404, "Artifact not found")
    if artifact.status == ArtifactStatus.STALE:
        raise HTTPException(409, "Artifact is stale. Regenerate first.")
    full_path = settings.artifact_storage / artifact.path
    if not full_path.exists():
        raise HTTPException(404, "Artifact file not found on disk")
    media_types = {"DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "PDF": "application/pdf", "JSON": "application/json", "CSV": "text/csv"}
    return FileResponse(str(full_path), media_type=media_types.get(artifact.type, "application/octet-stream"), filename=full_path.name)

@router.post("/meeting/{meeting_id}/generate", summary="Generate or regenerate DOCX artifact from canonical MeetingRecord")
async def generate_artifacts(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Builds or regenerates current DOCX artifact from the canonical MeetingRecord.
    Fulfills ADR-011: cheap artifact regeneration without rerunning ML/ASR stages.
    """
    from app.artifacts.docx_generator import DocxGenerator
    from app.models.meeting import Meeting
    from app.models.decisions import Decision
    from app.models.actions import ActionItem
    from app.models.questions import Question
    from app.models.participant import Participant, Speaker
    from app.models.transcript import TranscriptSegment
    from app.models.artifacts import ArtifactType

    meeting_res = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = meeting_res.scalar_one_or_none()
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    # Fetch canonical entities
    decisions_res = await db.execute(select(Decision).where(Decision.meeting_id == meeting_id))
    actions_res = await db.execute(select(ActionItem).where(ActionItem.originating_meeting_id == meeting_id))
    questions_res = await db.execute(select(Question).where(Question.meeting_id == meeting_id))
    parts_res = await db.execute(select(Participant).where(Participant.meeting_id == meeting_id))
    segments_res = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.start_ms)
    )

    participants = parts_res.scalars().all()
    part_name_map = {p.id: p.name for p in participants}

    # Fetch speakers to map transcript segments
    speakers_res = await db.execute(select(Speaker).where(Speaker.meeting_id == meeting_id))
    speaker_map = {}
    for spk in speakers_res.scalars().all():
        speaker_map[spk.id] = part_name_map.get(spk.resolved_participant_id, spk.label)

    meeting_export = {
        "title": meeting.title,
        "date": meeting.date.strftime("%Y-%m-%d %H:%M UTC") if meeting.date else "",
        "capture_mode": meeting.capture_mode,
        "lifecycle_status": meeting.lifecycle_status,
        "quality_metrics": meeting.quality_metrics or {},
        "summary": "Evidence-grounded Minutes of Meeting generated from canonical aggregate record.",
        "participants": [{"name": p.name, "role": p.role or "Team Member"} for p in participants],
        "decisions": [{"text": d.text, "status": d.status, "evidence_quote": ""} for d in decisions_res.scalars().all()],
        "action_items": [
            {
                "task": a.task,
                "owner": part_name_map.get(a.owner_id, "Unassigned"),
                "deadline": a.deadline.isoformat() if a.deadline else "TBD",
                "priority": a.priority,
            }
            for a in actions_res.scalars().all()
        ],
        "questions": [{"text": q.text, "answered": q.answered, "answer_text": q.answer_text} for q in questions_res.scalars().all()],
        "transcript_segments": [
            {
                "start_ms": s.start_ms,
                "speaker": speaker_map.get(s.speaker_id, "Speaker"),
                "text": s.text,
            }
            for s in segments_res.scalars().all()
        ],
    }

    doc_filename = f"Minutes_of_Meeting_{meeting_id[:8]}.docx"
    doc_rel_path = f"{meeting_id}/{doc_filename}"
    doc_abs_path = settings.artifact_storage / doc_rel_path
    DocxGenerator.generate(doc_abs_path, meeting_export)

    # Check for existing artifact to update or create
    art_res = await db.execute(
        select(Artifact).where(Artifact.meeting_id == meeting_id, Artifact.type == ArtifactType.DOCX)
    )
    art = art_res.scalars().first()
    if not art:
        art = Artifact(
            id=str(uuid.uuid4()),
            meeting_id=meeting_id,
            type=ArtifactType.DOCX,
            status=ArtifactStatus.CURRENT,
            path=doc_rel_path,
            file_size_bytes=doc_abs_path.stat().st_size,
        )
        db.add(art)
    else:
        art.status = ArtifactStatus.CURRENT
        art.stale_since = None
        art.stale_reason = None
        art.file_size_bytes = doc_abs_path.stat().st_size
        art.path = doc_rel_path

    await db.commit()

    return {
        "meeting_id": meeting_id,
        "artifact_id": art.id,
        "type": ArtifactType.DOCX,
        "status": ArtifactStatus.CURRENT,
        "path": doc_rel_path,
        "file_size_bytes": art.file_size_bytes,
        "message": "Artifact regenerated successfully.",
    }
