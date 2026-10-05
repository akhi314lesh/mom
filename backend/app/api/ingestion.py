"""api/ingestion.py — File upload and ingestion endpoint."""
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.capture import CaptureSession, CaptureSource, AudioSourceState
from app.models.meeting import Meeting, CaptureMode, MeetingLifecycle, ProcessingStatus, PrivacyMode
from app.pipeline.orchestrator import process_meeting_pipeline

router = APIRouter()

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}


@router.post("/upload", summary="Upload audio/video file and create a meeting")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(default=""),
    language: str = Form(default="en"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload an audio/video file.
    Creates a Meeting + CaptureSession, saves the file, queues processing.
    Phase 0: saves file + creates DB records. Processing is a stub.
    """
    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {suffix}. Allowed: {ALLOWED_AUDIO_EXTENSIONS}")

    # Validate size
    max_bytes = settings.storage_root and (500 * 1024 * 1024)
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, "File too large. Maximum 500 MB.")

    # Create meeting
    meeting_id = str(uuid.uuid4())
    meeting_title = title.strip() or (Path(file.filename or "").stem)
    meeting = Meeting(
        id=meeting_id,
        title=meeting_title,
        date=datetime.now(timezone.utc),
        capture_mode=CaptureMode.IMPORT,
        lifecycle_status=MeetingLifecycle.CAPTURING,
        processing_status=ProcessingStatus.QUEUED,
        privacy_mode=PrivacyMode.LOCAL,
        quality_metrics={
            "transcript_quality": 0.0, "speaker_attribution_quality": 0.0,
            "decision_certainty": 0.0, "action_extraction_confidence": 0.0,
            "grounding_coverage": 0.0, "overall_confidence": 0.0, "weak_areas": [],
        },
    )
    db.add(meeting)

    # Save file
    audio_dir = settings.audio_storage / meeting_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / (file.filename or f"audio{suffix}")
    audio_path.write_bytes(content)

    # Create capture session
    capture_session = CaptureSession(
        id=str(uuid.uuid4()),
        meeting_id=meeting_id,
        capture_mode=CaptureMode.IMPORT,
        audio_source_state=AudioSourceState.NO_AUDIO,  # import; no live audio
        evidence_manifest={
            "available_sources": ["IMPORT_FILE", "TIMESTAMPS"],
            "unavailable_sources": ["MICROPHONE", "SYSTEM_AUDIO", "MANUAL_MARKS"],
            "degradation_reason": None,
        },
        privacy_mode=PrivacyMode.LOCAL,
        is_active=False,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
    )
    db.add(capture_session)

    # Create capture source record
    source = CaptureSource(
        id=str(uuid.uuid4()),
        capture_session_id=capture_session.id,
        source_type="IMPORT_FILE",
        status="ACTIVE",
        file_path=str(audio_path),
    )
    db.add(source)

    await db.commit()

    # Queue progressive processing pipeline in background
    background_tasks.add_task(process_meeting_pipeline, meeting_id, str(audio_path))

    return {
        "meeting_id": meeting_id,
        "file_saved": str(audio_path),
        "status": "queued",
        "message": "File uploaded. Progressive processing pipeline started.",
    }


async def _process_meeting_stub(meeting_id: str, audio_path: str, language: str) -> None:
    """Invokes the full progressive processing pipeline."""
    from app.pipeline.orchestrator import process_meeting_pipeline
    await process_meeting_pipeline(meeting_id, audio_path)
