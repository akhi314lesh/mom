"""
seed.py — Automatic Demo Meeting seeder.

Seeds a realistic, grounded architecture review meeting if the database is empty.
Can be executed directly: python -m app.seed
or imported and called during startup lifespan.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, create_all_tables
from app.models.meeting import Meeting, CaptureMode, MeetingLifecycle, ProcessingStatus, PrivacyMode
from app.models.participant import Participant, Speaker
from app.models.transcript import TranscriptSegment
from app.models.evidence import Evidence
from app.models.semantic import SemanticEvent, SemanticEventType, ReviewState, MeetingTopic
from app.models.decisions import Decision, DecisionStatus
from app.models.actions import ActionItem, ActionItemStatus, ActionItemPriority
from app.models.questions import Question
from app.models.artifacts import Artifact, ArtifactType, ArtifactStatus
from app.artifacts.docx_generator import DocxGenerator
from app.artifacts.pdf_generator import PdfGenerator


DEMO_MEETING_ID = "demo-meeting-arch-review-001"


async def _ensure_demo_artifacts(db: AsyncSession) -> None:
    """Ensure DOCX and PDF artifacts exist on disk and in DB for the demo meeting."""
    settings.ensure_storage_dirs()
    docx_filename = f"MOM_{DEMO_MEETING_ID}.docx"
    pdf_filename = f"MOM_{DEMO_MEETING_ID}.pdf"
    docx_rel_path = f"{DEMO_MEETING_ID}/{docx_filename}"
    pdf_rel_path = f"{DEMO_MEETING_ID}/{pdf_filename}"
    docx_path = settings.artifact_storage / docx_rel_path
    pdf_path = settings.artifact_storage / pdf_rel_path

    meeting_export = {
        "title": "[DEMO DATA] Product Architecture Review",
        "date": (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M UTC"),
        "capture_mode": "IMPORT",
        "lifecycle_status": "FINALIZED",
        "quality_metrics": {
            "grounding_score": 0.98,
            "transcript_quality": 0.96,
            "speaker_attribution_quality": 0.95,
            "decision_certainty": 0.94,
            "grounding_coverage": 1.0,
            "action_extraction_confidence": 0.93,
            "overall_quality": 0.96,
        },
        "summary": "DEMO DATA: High-fidelity architecture review for MOM for meetings. Covers local SQLite WAL persistence, zero-API-key fallback mode, pure-Python PDF generation, and one-click operational startup.",
        "participants": [
            {"name": "Akhilesh", "role": "Engineering Lead"},
            {"name": "Priya", "role": "Staff Backend Architect"},
            {"name": "Rahul", "role": "Principal ML Engineer"},
            {"name": "Rohan", "role": "Product & Infrastructure Lead"},
        ],
        "decisions": [
            {
                "text": "Adopt SQLite with WAL mode for local zero-configuration persistence.",
                "status": "CONFIRMED",
                "evidence_quote": "For local persistence, we finalized SQLite with Write-Ahead Logging (WAL).",
            },
            {
                "text": "Use ReportLab for pure-Python, zero-native-dependency PDF generation.",
                "status": "CONFIRMED",
                "evidence_quote": "For document generation, we adopted ReportLab for pure-Python PDF generation alongside python-docx.",
            },
        ],
        "action_items": [
            {"task": "Finalize database migration integrity check and structured health endpoint contract.", "owner": "Priya", "deadline": str((datetime.now(timezone.utc) + timedelta(days=1)).date()), "priority": "HIGH"},
            {"task": "Verify stub adapter fallbacks to guarantee zero-API-key first-run experience.", "owner": "Rahul", "deadline": str((datetime.now(timezone.utc) + timedelta(days=1)).date()), "priority": "HIGH"},
            {"task": "Package one-click START_MOM launcher with automatic health probing and browser launch.", "owner": "Rohan", "deadline": str((datetime.now(timezone.utc) + timedelta(days=5)).date()), "priority": "CRITICAL"},
        ],
        "questions": [
            {"text": "What is the peak memory consumption of local diarization under extended 2-hour meetings?", "answered": False, "answer_text": None},
        ],
        "transcript_segments": [
            {"start_ms": 0, "speaker": "Akhilesh", "text": "Welcome everyone to the Product Architecture Review for MOM for meetings. Our objective is to ensure friction-free local execution, zero-configuration demo states, and strict evidence grounding across all captured records."},
            {"start_ms": 19000, "speaker": "Priya", "text": "Thanks Akhilesh. For local persistence, we finalized SQLite with Write-Ahead Logging (WAL). It provides sub-millisecond local reads, reliable ACID transactions, and eliminates any need for an external database daemon on the user's workstation."},
            {"start_ms": 43000, "speaker": "Rahul", "text": "On the ASR and diarization side, the system now runs out-of-the-box in DEMO mode with stub adapters that require zero API keys and zero local model downloads. Every semantic event links to exact transcript millisecond timestamps."},
            {"start_ms": 76000, "speaker": "Rohan", "text": "For document generation, we adopted ReportLab for pure-Python PDF generation alongside python-docx. This ensures cross-platform PDF builds without requiring native GTK or Cairo system libraries on Windows."},
            {"start_ms": 111000, "speaker": "Akhilesh", "text": "Confirmed. Let's make sure the one-click START_MOM launcher starts both FastAPI and Vite, validates health, and automatically opens the dashboard without user intervention. Can we lock the action items?"},
            {"start_ms": 136000, "speaker": "Priya", "text": "I will finalize the database migration integrity check and the structured health endpoint contract by end of day tomorrow."},
            {"start_ms": 161000, "speaker": "Rahul", "text": "I will verify the stub adapter fallbacks to guarantee a 100% reliable first-run experience with zero cloud dependencies."},
            {"start_ms": 186000, "speaker": "Rohan", "text": "I will package the one-click START_MOM launcher with automatic health probing and browser launch."},
        ],
    }

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    DocxGenerator.generate(docx_path, meeting_export)
    PdfGenerator.generate(pdf_path, meeting_export)

    art_res = await db.execute(select(Artifact).where(Artifact.meeting_id == DEMO_MEETING_ID))
    existing_types = {a.type for a in art_res.scalars().all()}

    if ArtifactType.DOCX.value not in existing_types:
        docx_art = Artifact(
            id=str(uuid.uuid4()),
            meeting_id=DEMO_MEETING_ID,
            type=ArtifactType.DOCX.value,
            status=ArtifactStatus.CURRENT.value,
            path=docx_rel_path,
            file_size_bytes=docx_path.stat().st_size if docx_path.exists() else 0,
        )
        db.add(docx_art)

    if ArtifactType.PDF.value not in existing_types:
        pdf_art = Artifact(
            id=str(uuid.uuid4()),
            meeting_id=DEMO_MEETING_ID,
            type=ArtifactType.PDF.value,
            status=ArtifactStatus.CURRENT.value,
            path=pdf_rel_path,
            file_size_bytes=pdf_path.stat().st_size if pdf_path.exists() else 0,
        )
        db.add(pdf_art)

    await db.commit()


async def seed_demo_meeting(db: AsyncSession) -> str:
    """
    Seeds a high-fidelity Demo Meeting if no meetings exist.
    Returns the meeting ID (newly seeded or existing).
    """
    existing_demo = await db.execute(select(Meeting).where(Meeting.id == DEMO_MEETING_ID))
    if existing_demo.scalar_one_or_none():
        await _ensure_demo_artifacts(db)
        return DEMO_MEETING_ID

    now = datetime.now(timezone.utc)
    meeting_date = now - timedelta(hours=2)

    quality_metrics = {
        "grounding_score": 0.98,
        "transcript_quality": 0.96,
        "speaker_attribution_quality": 0.95,
        "decision_certainty": 0.94,
        "grounding_coverage": 1.0,
        "action_extraction_confidence": 0.93,
        "confidence_distribution": {"high": 14, "medium": 1, "low": 0},
        "contradiction_count": 0,
        "unresolved_questions": 1,
        "overall_quality": 0.96,
        "word_count": 285,
        "audio_duration_seconds": 210,
        "speakers_detected": 4,
        "provenance_intact": True,
        "weak_areas": [],
    }

    # 1. Root Meeting
    meeting = Meeting(
        id=DEMO_MEETING_ID,
        title="[DEMO DATA] Product Architecture Review",
        date=meeting_date,
        capture_mode=CaptureMode.IMPORT,
        lifecycle_status=MeetingLifecycle.FINALIZED,
        processing_status=ProcessingStatus.COMPLETE,
        privacy_mode=PrivacyMode.LOCAL,
        quality_metrics=quality_metrics,
        description=(
            "DEMO DATA: High-fidelity architecture review for MOM for meetings. "
            "Covers local SQLite WAL storage, zero-API-key fallback mode, "
            "pure-Python PDF artifact generation, and one-click operational startup."
        ),
    )
    db.add(meeting)

    # 2. Participants
    p_akhilesh = Participant(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        name="Akhilesh",
        email="akhilesh@example.com",
        role="Engineering Lead",
        is_self=True,
        aliases=["Akhilesh", "Akhil", "AK"],
    )
    p_priya = Participant(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        name="Priya",
        email="priya@example.com",
        role="Staff Backend Architect",
        is_self=False,
        aliases=["Priya"],
    )
    p_rahul = Participant(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        name="Rahul",
        email="rahul@example.com",
        role="Principal ML Engineer",
        is_self=False,
        aliases=["Rahul"],
    )
    p_rohan = Participant(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        name="Rohan",
        email="rohan@example.com",
        role="Product & Infrastructure Lead",
        is_self=False,
        aliases=["Rohan"],
    )
    db.add_all([p_akhilesh, p_priya, p_rahul, p_rohan])

    # 3. Speakers
    spk_1 = Speaker(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        label="SPEAKER_1",
        resolved_participant_id=p_akhilesh.id,
        resolution_confidence=1.0,
        resolution_source="SYSTEM",
        total_speaking_time_ms=45000,
    )
    spk_2 = Speaker(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        label="SPEAKER_2",
        resolved_participant_id=p_priya.id,
        resolution_confidence=0.98,
        resolution_source="SYSTEM",
        total_speaking_time_ms=50000,
    )
    spk_3 = Speaker(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        label="SPEAKER_3",
        resolved_participant_id=p_rahul.id,
        resolution_confidence=0.97,
        resolution_source="SYSTEM",
        total_speaking_time_ms=55000,
    )
    spk_4 = Speaker(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        label="SPEAKER_4",
        resolved_participant_id=p_rohan.id,
        resolution_confidence=0.99,
        resolution_source="SYSTEM",
        total_speaking_time_ms=60000,
    )
    db.add_all([spk_1, spk_2, spk_3, spk_4])

    # 4. Meeting Topics
    t1 = MeetingTopic(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        title="Architecture & Local-First Storage",
        start_ms=0,
        end_ms=55000,
        importance=0.95,
    )
    t2 = MeetingTopic(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        title="Speech Recognition & Grounded Provenance",
        start_ms=55000,
        end_ms=120000,
        importance=0.92,
    )
    t3 = MeetingTopic(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        title="Document Artifact Generation & One-Click Launch",
        start_ms=120000,
        end_ms=210000,
        importance=0.98,
    )
    db.add_all([t1, t2, t3])

    # 5. Transcript Segments & Evidence
    raw_segments = [
        (
            spk_1.id,
            0,
            18000,
            "Welcome everyone to the Product Architecture Review for MOM for meetings. Our objective is to ensure friction-free local execution, zero-configuration demo states, and strict evidence grounding across all captured records.",
            0.99,
        ),
        (
            spk_2.id,
            19000,
            42000,
            "Thanks Akhilesh. For local persistence, we finalized SQLite with Write-Ahead Logging (WAL). It provides sub-millisecond local reads, reliable ACID transactions, and eliminates any need for an external database daemon on the user's workstation.",
            0.98,
        ),
        (
            spk_3.id,
            43000,
            75000,
            "On the ASR and diarization side, the system now runs out-of-the-box in DEMO mode with stub adapters that require zero API keys and zero local model downloads. Every semantic event links to exact transcript millisecond timestamps.",
            0.97,
        ),
        (
            spk_4.id,
            76000,
            110000,
            "For document generation, we adopted ReportLab for pure-Python PDF generation alongside python-docx. This ensures cross-platform PDF builds without requiring native GTK or Cairo system libraries on Windows.",
            0.99,
        ),
        (
            spk_1.id,
            111000,
            135000,
            "Confirmed. Let's make sure the one-click START_MOM launcher starts both FastAPI and Vite, validates health, and automatically opens the dashboard without user intervention. Can we lock the action items?",
            0.98,
        ),
        (
            spk_2.id,
            136000,
            160000,
            "I will finalize the database migration integrity check and the structured health endpoint contract by end of day tomorrow.",
            0.99,
        ),
        (
            spk_3.id,
            161000,
            185000,
            "I will verify the stub adapter fallbacks to guarantee a 100% reliable first-run experience with zero cloud dependencies.",
            0.98,
        ),
        (
            spk_4.id,
            186000,
            210000,
            "I will package the one-click START_MOM launcher with automatic health probing and browser launch.",
            0.99,
        ),
    ]

    segments = []
    evidences = []
    for spk_id, start_ms, end_ms, text, conf in raw_segments:
        seg_id = str(uuid.uuid4())
        seg = TranscriptSegment(
            id=seg_id,
            meeting_id=DEMO_MEETING_ID,
            speaker_id=spk_id,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            language="en",
            asr_confidence=conf,
            is_edited=False,
            source_modality="AUDIO",
        )
        segments.append(seg)

        ev = Evidence(
            id=str(uuid.uuid4()),
            meeting_id=DEMO_MEETING_ID,
            segment_id=seg_id,
            source_type="TRANSCRIPT",
            source_modality="AUDIO",
            timestamp_ms=start_ms,
            raw_text=text,
            confidence=conf,
            is_immutable=True,
        )
        evidences.append(ev)

    db.add_all(segments)
    db.add_all(evidences)

    # 6. Semantic Events
    se_dec1 = SemanticEvent(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        event_type=SemanticEventType.DECISION_CONFIRMED.value,
        text="Adopt SQLite with WAL mode for local zero-configuration persistence.",
        evidence_ids=[evidences[1].id],
        start_ms=19000,
        end_ms=42000,
        confidence=0.98,
        extraction_stage="DECISION_EXTRACTION",
        review_state=ReviewState.CONFIRMED.value,
    )
    se_dec2 = SemanticEvent(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        event_type=SemanticEventType.DECISION_CONFIRMED.value,
        text="Use ReportLab for pure-Python, zero-native-dependency PDF generation.",
        evidence_ids=[evidences[3].id],
        start_ms=76000,
        end_ms=110000,
        confidence=0.99,
        extraction_stage="DECISION_EXTRACTION",
        review_state=ReviewState.CONFIRMED.value,
    )
    se_act1 = SemanticEvent(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        event_type=SemanticEventType.ACTION_ITEM.value,
        text="Finalize database migration integrity check and structured health endpoint contract.",
        evidence_ids=[evidences[5].id],
        start_ms=136000,
        end_ms=160000,
        confidence=0.99,
        extraction_stage="ACTION_EXTRACTION",
        review_state=ReviewState.CONFIRMED.value,
    )
    se_act2 = SemanticEvent(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        event_type=SemanticEventType.ACTION_ITEM.value,
        text="Verify stub adapter fallbacks to guarantee zero-API-key first-run experience.",
        evidence_ids=[evidences[6].id],
        start_ms=161000,
        end_ms=185000,
        confidence=0.98,
        extraction_stage="ACTION_EXTRACTION",
        review_state=ReviewState.CONFIRMED.value,
    )
    se_act3 = SemanticEvent(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        event_type=SemanticEventType.ACTION_ITEM.value,
        text="Package one-click START_MOM launcher with automatic health probing and browser launch.",
        evidence_ids=[evidences[7].id],
        start_ms=186000,
        end_ms=210000,
        confidence=0.99,
        extraction_stage="ACTION_EXTRACTION",
        review_state=ReviewState.CONFIRMED.value,
    )
    db.add_all([se_dec1, se_dec2, se_act1, se_act2, se_act3])

    # 7. Decisions
    d1 = Decision(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        semantic_event_id=se_dec1.id,
        text="Adopt SQLite with WAL mode for local zero-configuration persistence.",
        status=DecisionStatus.CONFIRMED,
        evidence_ids=[evidences[1].id],
        confidence=0.98,
        review_state="CONFIRMED",
    )
    d2 = Decision(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        semantic_event_id=se_dec2.id,
        text="Use ReportLab for pure-Python, zero-native-dependency PDF generation.",
        status=DecisionStatus.CONFIRMED,
        evidence_ids=[evidences[3].id],
        confidence=0.99,
        review_state="CONFIRMED",
    )
    db.add_all([d1, d2])

    # 8. Action Items
    tomorrow = (now + timedelta(days=1)).date()
    next_week = (now + timedelta(days=5)).date()

    a1 = ActionItem(
        id=str(uuid.uuid4()),
        originating_meeting_id=DEMO_MEETING_ID,
        originating_timestamp_ms=136000,
        task="Finalize database migration integrity check and structured health endpoint contract.",
        owner_id=p_priya.id,
        owner_confidence=0.99,
        deadline=tomorrow,
        deadline_confidence=0.95,
        status=ActionItemStatus.PENDING,
        priority=ActionItemPriority.HIGH,
        evidence_ids=[evidences[5].id],
        confidence=0.99,
        review_state="CONFIRMED",
    )
    a2 = ActionItem(
        id=str(uuid.uuid4()),
        originating_meeting_id=DEMO_MEETING_ID,
        originating_timestamp_ms=161000,
        task="Verify stub adapter fallbacks to guarantee zero-API-key first-run experience.",
        owner_id=p_rahul.id,
        owner_confidence=0.98,
        deadline=tomorrow,
        deadline_confidence=0.95,
        status=ActionItemStatus.IN_PROGRESS,
        priority=ActionItemPriority.HIGH,
        evidence_ids=[evidences[6].id],
        confidence=0.98,
        review_state="CONFIRMED",
    )
    a3 = ActionItem(
        id=str(uuid.uuid4()),
        originating_meeting_id=DEMO_MEETING_ID,
        originating_timestamp_ms=186000,
        task="Package one-click START_MOM launcher with automatic health probing and browser launch.",
        owner_id=p_rohan.id,
        owner_confidence=0.99,
        deadline=next_week,
        deadline_confidence=0.90,
        status=ActionItemStatus.COMPLETED,
        priority=ActionItemPriority.CRITICAL,
        evidence_ids=[evidences[7].id],
        confidence=0.99,
        review_state="CONFIRMED",
    )
    db.add_all([a1, a2, a3])

    # 9. Question
    q1 = Question(
        id=str(uuid.uuid4()),
        meeting_id=DEMO_MEETING_ID,
        text="What is the peak memory consumption of local diarization under extended 2-hour meetings?",
        asker_id=p_akhilesh.id,
        answered=False,
        answer_text=None,
        evidence_ids=[evidences[0].id],
        confidence=0.92,
    )
    db.add(q1)

    await db.commit()

    # 10. Generate artifacts
    await _ensure_demo_artifacts(db)

    return DEMO_MEETING_ID


async def main():
    await create_all_tables()
    async with AsyncSessionLocal() as db:
        meeting_id = await seed_demo_meeting(db)
        print(f"[OK] Seeded demo meeting ID: {meeting_id}")


if __name__ == "__main__":
    asyncio.run(main())
