"""
pipeline/corrections.py — Human Correction and Invalidation Service.

Implements architectural invariants from ADR-008, ADR-010, and ADR-011:
1. Corrections create NEW immutable Evidence records (source_type="HUMAN_CORRECTION")
2. Prior Evidence is NEVER mutated or deleted.
3. Affected Artifacts are marked STALE with a stale_reason and timestamp.
4. Downstream processing stages are marked INVALIDATED without re-running upstream ASR/Diarization.
5. Cheap regeneration produces current artifacts directly from canonical DB state.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import manager as ws_manager
from app.models.artifacts import Artifact, ArtifactStatus
from app.models.evidence import Evidence
from app.models.processing import ProcessingRun, get_downstream_stages


async def apply_human_correction(
    db: AsyncSession,
    meeting_id: str,
    target_type: str,
    target_id: str,
    field: str,
    old_value: Any,
    new_value: Any,
    origin_stage: str = "SEMANTIC",
) -> dict[str, Any]:
    """
    Applies human correction, appends immutable Evidence, invalidates only
    downstream stages, marks artifacts STALE, and regenerates DOCX artifact.
    """
    now = datetime.now(timezone.utc)

    # 1. Create immutable HUMAN_CORRECTION Evidence (ADR-008)
    corr_evidence = Evidence(
        id=str(uuid.uuid4()),
        meeting_id=meeting_id,
        source_type="HUMAN_CORRECTION",
        source_modality="TEXT",
        raw_text=f"Human correction on {target_type} ({field}): '{old_value}' -> '{new_value}'",
        confidence=1.0,
        is_immutable=True,
    )
    db.add(corr_evidence)

    # 2. Dependency-aware invalidation of downstream ProcessingRuns (ADR-010)
    downstream_stages = get_downstream_stages(origin_stage) + [origin_stage]
    runs_res = await db.execute(
        select(ProcessingRun).where(
            ProcessingRun.meeting_id == meeting_id,
            ProcessingRun.stage.in_(downstream_stages),
            ProcessingRun.status == "COMPLETE",
        )
    )
    for run in runs_res.scalars().all():
        run.status = "INVALIDATED"
        run.invalidated_at = now
        run.invalidation_reason = f"Human correction on {target_type}.{field}"

    # 3. Mark existing artifacts STALE (ADR-011)
    arts_res = await db.execute(
        select(Artifact).where(Artifact.meeting_id == meeting_id)
    )
    for art in arts_res.scalars().all():
        art.status = ArtifactStatus.STALE
        art.stale_since = now
        art.stale_reason = f"Human correction on {target_type}.{field} ('{new_value}')"

    await db.commit()

    # 4. Regenerate current DOCX artifact directly from canonical MeetingRecord (ADR-011)
    # Expensive ASR / ML stages are NOT rerun!
    from app.api.artifacts import generate_artifacts
    regen_result = await generate_artifacts(meeting_id, db)

    # 5. Broadcast live WebSocket update
    await ws_manager.broadcast(meeting_id, {
        "type": "CORRECTION_APPLIED",
        "meeting_id": meeting_id,
        "target_type": target_type,
        "target_id": target_id,
        "field": field,
        "new_value": str(new_value),
        "evidence_id": corr_evidence.id,
        "artifact_status": "CURRENT",
    })

    return {
        "meeting_id": meeting_id,
        "evidence_id": corr_evidence.id,
        "target_type": target_type,
        "field": field,
        "new_value": new_value,
        "invalidated_stages": downstream_stages,
        "artifact_regen": regen_result,
    }
