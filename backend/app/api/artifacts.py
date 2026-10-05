"""api/artifacts.py — DOCX/PDF download endpoints."""
import os
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

@router.post("/meeting/{meeting_id}/generate", summary="Generate DOCX and PDF artifacts")
async def generate_artifacts(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Phase 1: runs DocxGenerator + PdfGenerator. Phase 0: stub response."""
    return {"meeting_id": meeting_id, "status": "pending", "message": "Artifact generation implemented in Phase 1."}
