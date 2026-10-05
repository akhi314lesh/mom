"""
tests/test_phase6_continuity_knowledge.py — Test suite for Phase 6.

Validates:
1. Cross-Meeting ActionItem continuity tracking (originating_meeting_id vs last_updated_meeting_id).
2. Continuity evidence creation (source_type="CONTINUITY_UPDATE", is_immutable=True).
3. Action history endpoint lineage and evidence chain.
4. Knowledge accretion pipeline (confirmed decisions -> KnowledgeItems, terminology extraction).
5. Strict Invariant: verified=True requires HUMAN or system confidence >= 0.85; INFERRED is NEVER verified.
6. Human verification of KnowledgeItems and Terminology.
7. People Directory cross-meeting metrics (meetings count, action item counts, speaking time).
8. Cross-meeting contradiction query endpoint.
"""
import sys
import os
import uuid
import asyncio
from datetime import datetime, date, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.database import AsyncSessionLocal, create_all_tables
from app.models.meeting import Meeting, MeetingLifecycle, ProcessingStatus, CaptureMode
from app.models.participant import Participant, Speaker
from app.models.transcript import TranscriptSegment
from app.models.evidence import Evidence
from app.models.semantic import SemanticEvent
from app.models.decisions import Decision, DecisionStatus
from app.models.actions import ActionItem, ActionItemStatus, ActionItemPriority
from app.models.contradictions import Contradiction, ContradictionType
from app.models.knowledge import KnowledgeItem, TerminologyEntry
from app.pipeline.continuity import continuity_resolver
from app.pipeline.knowledge_accretion import knowledge_accretion_engine
from app.api.continuity import list_cross_meeting_actions, get_action_history, update_action_status_continuity
from app.api.knowledge import list_knowledge, verify_knowledge, list_terminology, upsert_terminology, list_cross_meeting_contradictions
from app.api.people import get_participant_directory, get_participant_history


async def run_phase6_tests():
    print("======================================================================")
    print("PHASE 6 VALIDATION: Continuity + Organizational Memory + Terminology")
    print("======================================================================")

    await create_all_tables()

    async with AsyncSessionLocal() as db:
        # -------------------------------------------------------------
        # STEP 1: Seed Meeting 1 and Meeting 2 with Participants
        # -------------------------------------------------------------
        print("\n[STEP 1] Setting up Meeting 1 and Meeting 2 in organizational history...")
        m1_id = str(uuid.uuid4())
        m2_id = str(uuid.uuid4())

        m1 = Meeting(
            id=m1_id,
            title="Backend Sprint Planning",
            date=datetime.now(timezone.utc),
            capture_mode=CaptureMode.RECORDING,
            lifecycle_status=MeetingLifecycle.REVIEWING,
            processing_status=ProcessingStatus.COMPLETE,
        )
        m2 = Meeting(
            id=m2_id,
            title="Backend Architecture Sync",
            date=datetime.now(timezone.utc),
            capture_mode=CaptureMode.OVERLAY,
            lifecycle_status=MeetingLifecycle.REVIEWING,
            processing_status=ProcessingStatus.COMPLETE,
        )
        db.add(m1)
        db.add(m2)

        # Participants in M1
        p_akhilesh = Participant(
            id=str(uuid.uuid4()),
            meeting_id=m1_id,
            name="Akhilesh",
            role="Tech Lead",
        )
        p_priya = Participant(
            id=str(uuid.uuid4()),
            meeting_id=m1_id,
            name="Priya",
            role="Data Architect",
        )
        db.add(p_akhilesh)
        db.add(p_priya)

        # Speakers with speaking times
        spk1 = Speaker(
            id=str(uuid.uuid4()),
            meeting_id=m1_id,
            label="SPEAKER_0",
            resolved_participant_id=p_akhilesh.id,
            resolution_confidence=0.98,
            total_speaking_time_ms=120000,
        )
        spk2 = Speaker(
            id=str(uuid.uuid4()),
            meeting_id=m1_id,
            label="SPEAKER_1",
            resolved_participant_id=p_priya.id,
            resolution_confidence=0.95,
            total_speaking_time_ms=90000,
        )
        db.add(spk1)
        db.add(spk2)

        # M1 Decisions
        sem_d1 = SemanticEvent(
            id=str(uuid.uuid4()),
            meeting_id=m1_id,
            start_ms=5000,
            end_ms=10000,
            text="Adopt FastAPI for high performance asynchronous web services",
            event_type="DECISION",
            confidence=0.95,
        )
        db.add(sem_d1)

        d1 = Decision(
            id=str(uuid.uuid4()),
            meeting_id=m1_id,
            semantic_event_id=sem_d1.id,
            text="Adopt FastAPI for high performance asynchronous web services",
            status=DecisionStatus.CONFIRMED,
            confidence=0.95,
            review_state="CONFIRMED",
        )
        db.add(d1)

        # M1 Evidence
        ev1 = Evidence(
            id=str(uuid.uuid4()),
            meeting_id=m1_id,
            source_type="ASR",
            raw_text="Let us build the core authentication scaffolding by Friday",
            confidence=0.95,
            is_immutable=True,
        )
        db.add(ev1)

        # M1 Action Item: Authentication scaffolding
        act1 = ActionItem(
            id=str(uuid.uuid4()),
            originating_meeting_id=m1_id,
            task="Build core authentication scaffolding with JWT",
            owner_id=p_akhilesh.id,
            owner_confidence=0.92,
            deadline=date(2026, 10, 15),
            deadline_confidence=0.90,
            status=ActionItemStatus.PENDING,
            priority=ActionItemPriority.HIGH,
            evidence_ids=[ev1.id],
            confidence=0.94,
            review_state="PENDING",
            last_updated_meeting_id=None,
        )
        db.add(act1)
        await db.commit()

        print(f" -> Meeting 1 created: {m1.title} ({m1_id[:8]}) with 1 ActionItem ({act1.task})")

        # -------------------------------------------------------------
        # STEP 2: Meeting 2 Discusses M1 Action Item ("finished", "completed")
        # -------------------------------------------------------------
        print("\n[STEP 2] Simulating Meeting 2 transcript discussing completion of M1 task...")
        m2_seg = TranscriptSegment(
            id=str(uuid.uuid4()),
            meeting_id=m2_id,
            speaker_id=spk1.id,
            start_ms=12000,
            end_ms=19000,
            text="Great news team, we finished and completed the authentication scaffolding with JWT as planned.",
            asr_confidence=0.96,
        )
        db.add(m2_seg)
        await db.commit()

        # Run Continuity Resolver
        print(" -> Running ContinuityResolver.resolve_meeting_continuity...")
        updates = await continuity_resolver.resolve_meeting_continuity(db, m2_id)
        up = next((u for u in updates if u["action_id"] == act1.id), None)
        assert up is not None, f"Update for action {act1.id} should be present in updates"
        assert up["new_status"] == ActionItemStatus.COMPLETED
        assert up["last_updated_meeting_id"] == m2_id

        # Verify ActionItem in DB
        await db.refresh(act1)
        assert act1.status == ActionItemStatus.COMPLETED
        assert act1.last_updated_meeting_id == m2_id
        assert len(act1.evidence_ids) >= 2

        # Verify Continuity Evidence
        ev_res = await db.execute(select(Evidence).where(Evidence.id == up["evidence_id"]))
        cont_ev = ev_res.scalar_one_or_none()
        assert cont_ev is not None
        assert cont_ev.source_type == "CONTINUITY_UPDATE"
        assert cont_ev.meeting_id == m2_id
        assert cont_ev.is_immutable is True

        print(f" -> SUCCESS: ActionItem status updated to COMPLETED by M2. Last updated meeting set to {m2_id[:8]}.")
        print(f" -> Continuity Evidence recorded immutably: '{cont_ev.raw_text}'")

        # -------------------------------------------------------------
        # STEP 3: Action Lineage and History Endpoint
        # -------------------------------------------------------------
        print("\n[STEP 3] Verifying action continuity history endpoint...")
        history = await get_action_history(action_id=act1.id, db=db)
        assert history["id"] == act1.id
        assert history["status"] == ActionItemStatus.COMPLETED
        assert history["originating_meeting"]["id"] == m1_id
        assert history["last_updated_meeting"]["id"] == m2_id
        assert len(history["evidence_chain"]) >= 2
        print(f" -> Originating meeting: {history['originating_meeting']['title']}")
        print(f" -> Last updated meeting: {history['last_updated_meeting']['title']}")
        print(f" -> Evidence chain items: {len(history['evidence_chain'])}")

        # -------------------------------------------------------------
        # STEP 4: Knowledge Accretion Engine & Invariant Verification
        # -------------------------------------------------------------
        print("\n[STEP 4] Running KnowledgeAccretionEngine on Meeting 1 & Meeting 2...")
        # Add segment with technical terminology in M1
        m1_term_seg = TranscriptSegment(
            id=str(uuid.uuid4()),
            meeting_id=m1_id,
            speaker_id=spk1.id,
            start_ms=20000,
            end_ms=26000,
            text="We will use FastAPI for backend and WASAPI loopback for capturing Windows system audio.",
            asr_confidence=0.95,
        )
        db.add(m1_term_seg)
        await db.commit()

        accretion_res = await knowledge_accretion_engine.accrete_from_meeting(db, m1_id)
        print(f" -> Accretion output: {accretion_res}")
        assert accretion_res["accreted_knowledge_items"] >= 1
        assert accretion_res["accreted_terminology"] >= 1

        # Check KnowledgeItems in DB
        k_res = await db.execute(select(KnowledgeItem))
        k_items = k_res.scalars().all()
        decision_items = [k for k in k_items if k.type == "DECISION"]
        assert len(decision_items) >= 1
        d_k = decision_items[0]
        print(f" -> Accreted Decision Item: '{d_k.content}' (verified={d_k.verified}, source={d_k.verification_source}, conf={d_k.confidence})")

        # INVARIANT CHECK:
        if d_k.verification_source == "INFERRED":
            assert d_k.verified is False, "INFERRED alone must NEVER have verified=True!"
        elif d_k.verification_source == "SYSTEM":
            assert d_k.confidence >= 0.85, "SYSTEM verified requires confidence >= 0.85"

        # -------------------------------------------------------------
        # STEP 5: Human Knowledge Verification Flow
        # -------------------------------------------------------------
        print("\n[STEP 5] Testing human verification flow on KnowledgeItem...")
        # Create an unverified inferred item
        inferred_item = KnowledgeItem(
            id=str(uuid.uuid4()),
            type="FACT",
            content="Team prefers synchronous daily standup meetings at 10 AM",
            source_meeting_ids=[m1_id],
            confidence=0.70,
            verified=False,
            verification_source="INFERRED",
        )
        db.add(inferred_item)
        await db.commit()

        # Human verifies it
        verified_resp = await verify_knowledge(item_id=inferred_item.id, body={"verified": True}, db=db)
        assert verified_resp["verified"] is True
        assert verified_resp["verification_source"] == "HUMAN"
        assert verified_resp["confidence"] == 1.0
        print(" -> Verified by human: source set to HUMAN, confidence set to 1.0.")

        # -------------------------------------------------------------
        # STEP 6: Terminology Dictionary Accretion & Verification
        # -------------------------------------------------------------
        print("\n[STEP 6] Testing Terminology dictionary listing and upsert...")
        terms = await list_terminology(db=db)
        term_names = [t["term"] for t in terms]
        print(f" -> Extracted terms: {term_names}")
        assert "FastAPI" in term_names or "WASAPI" in term_names

        # User adds a custom term
        upsert_res = await upsert_terminology(
            body={
                "term": "OODA",
                "canonical_meaning": "Observe-Orient-Decide-Act loop governing system autonomy",
                "aliases": ["OODA Loop"],
            },
            db=db,
        )
        assert upsert_res["term"] == "OODA"
        assert upsert_res["verified"] is True
        print(f" -> Human added term '{upsert_res['term']}' successfully verified.")

        # -------------------------------------------------------------
        # STEP 7: People Directory Cross-Meeting Metrics
        # -------------------------------------------------------------
        print("\n[STEP 7] Testing People Directory with cross-meeting metrics...")
        directory = await get_participant_directory(db=db)
        assert len(directory) >= 2

        akhilesh_dir = next((p for p in directory if p["name"] == "Akhilesh"), None)
        assert akhilesh_dir is not None
        print(f" -> Participant: {akhilesh_dir['name']}")
        print(f"    Meetings attended: {akhilesh_dir['meetings_count']}")
        print(f"    Total speaking time: {akhilesh_dir['total_speaking_time_min']} mins")
        print(f"    Completed actions: {akhilesh_dir['completed_actions_count']}")
        print(f"    Resolved speaker labels: {akhilesh_dir['resolved_speaker_labels']}")
        assert akhilesh_dir["completed_actions_count"] >= 1
        assert "SPEAKER_0" in akhilesh_dir["resolved_speaker_labels"]

        # Participant History
        p_hist = await get_participant_history(participant_id=p_akhilesh.id, db=db)
        assert len(p_hist["meetings_attended"]) >= 1
        assert len(p_hist["actions_assigned"]) >= 1
        print(f" -> Participant history verified with {len(p_hist['meetings_attended'])} meeting(s) and {len(p_hist['actions_assigned'])} action(s).")

        # -------------------------------------------------------------
        # STEP 8: Cross-Meeting Contradictions Endpoint
        # -------------------------------------------------------------
        print("\n[STEP 8] Testing cross-meeting contradictions endpoint...")
        # Create a cross-meeting contradiction record
        con = Contradiction(
            id=str(uuid.uuid4()),
            meeting_id=m2_id,
            event_a_id=d1.id,
            event_b_id=str(uuid.uuid4()),
            description="Reversal: Meeting 1 decided FastAPI, Meeting 2 proposed Flask",
            contradiction_type=ContradictionType.CROSS_MEETING,
            is_cross_meeting=True,
            meeting_a_id=m1_id,
            meeting_b_id=m2_id,
            review_state="PENDING",
            confidence=0.92,
        )
        db.add(con)
        await db.commit()

        con_list = await list_cross_meeting_contradictions(db=db)
        assert len(con_list) >= 1
        c_item = next((c for c in con_list if c["id"] == con.id), None)
        assert c_item is not None
        assert c_item["meeting_a_title"] == "Backend Sprint Planning"
        assert c_item["meeting_b_title"] == "Backend Architecture Sync"
        print(f" -> Cross-meeting contradiction found between '{c_item['meeting_a_title']}' and '{c_item['meeting_b_title']}'.")

    print("\n======================================================================")
    print("ALL PHASE 6 AUTOMATED TESTS PASSED CLEANLY!")
    print("======================================================================")


if __name__ == "__main__":
    asyncio.run(run_phase6_tests())
