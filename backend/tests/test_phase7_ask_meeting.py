"""
tests/test_phase7_ask_meeting.py — Automated test suite for Phase 7 (Ask the Meeting).

Validates:
1. Query classification (ACTION_OWNER, DECISION_STATUS, CONTRADICTION, FACTUAL, GENERAL).
2. Evidence retrieval across actions, decisions, transcript segments, and contradictions.
3. Natural language answer synthesis with citation of AnswerSource items.
4. Strict Invariant: Ungrounded query returns grounded=False, confidence=0.0, sources=[].
5. Meeting-scoped query vs organizational query.
"""
import sys
import os
import uuid
import asyncio
from datetime import datetime, timezone, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal, create_all_tables
from app.models.meeting import Meeting, MeetingLifecycle, ProcessingStatus, CaptureMode
from app.models.participant import Participant
from app.models.decisions import Decision, DecisionStatus
from app.models.actions import ActionItem, ActionItemStatus, ActionItemPriority
from app.models.contradictions import Contradiction, ContradictionType
from app.models.semantic import SemanticEvent
from app.models.transcript import TranscriptSegment
from app.models.evidence import Evidence
from app.pipeline.query_engine import query_engine
from app.api.query import ask_meeting, ask_single_meeting


async def run_phase7_tests():
    print("======================================================================")
    print("PHASE 7 VALIDATION: Ask the Meeting (Evidence-Grounded Query Engine)")
    print("======================================================================")

    await create_all_tables()

    async with AsyncSessionLocal() as db:
        # -------------------------------------------------------------
        # STEP 1: Seed Test Data
        # -------------------------------------------------------------
        print("\n[STEP 1] Seeding meeting, participant, decision, action, and contradiction...")
        m_id = str(uuid.uuid4())
        meeting = Meeting(
            id=m_id,
            title="Authentication & Core Infrastructure",
            date=datetime.now(timezone.utc),
            capture_mode=CaptureMode.RECORDING,
            lifecycle_status=MeetingLifecycle.REVIEWING,
            processing_status=ProcessingStatus.COMPLETE,
        )
        db.add(meeting)

        participant = Participant(
            id=str(uuid.uuid4()),
            meeting_id=m_id,
            name="Akhilesh",
            role="Tech Lead",
        )
        db.add(participant)

        # Transcript segment
        seg = TranscriptSegment(
            id=str(uuid.uuid4()),
            meeting_id=m_id,
            start_ms=10000,
            end_ms=18000,
            text="I will take responsibility for building the JWT authentication scaffolding by next Friday.",
            asr_confidence=0.96,
        )
        db.add(seg)

        # Evidence
        ev = Evidence(
            id=str(uuid.uuid4()),
            meeting_id=m_id,
            segment_id=seg.id,
            source_type="ASR",
            raw_text=seg.text,
            confidence=0.96,
            is_immutable=True,
        )
        db.add(ev)

        # Semantic Event for Decision
        sem_dec = SemanticEvent(
            id=str(uuid.uuid4()),
            meeting_id=m_id,
            start_ms=25000,
            end_ms=30000,
            text="Use FastAPI as the core API framework",
            event_type="DECISION",
            confidence=0.94,
        )
        db.add(sem_dec)

        # Decision
        decision = Decision(
            id=str(uuid.uuid4()),
            meeting_id=m_id,
            semantic_event_id=sem_dec.id,
            text="Use FastAPI as the core API framework",
            status=DecisionStatus.CONFIRMED,
            confidence=0.94,
            review_state="CONFIRMED",
        )
        db.add(decision)

        # Action Item
        action = ActionItem(
            id=str(uuid.uuid4()),
            originating_meeting_id=m_id,
            task="Build JWT authentication scaffolding",
            owner_id=participant.id,
            owner_confidence=0.95,
            deadline=date(2026, 10, 15),
            deadline_confidence=0.92,
            status=ActionItemStatus.IN_PROGRESS,
            priority=ActionItemPriority.HIGH,
            evidence_ids=[ev.id],
            confidence=0.95,
            review_state="CONFIRMED",
        )
        db.add(action)

        # Contradiction
        contradiction = Contradiction(
            id=str(uuid.uuid4()),
            meeting_id=m_id,
            event_a_id=decision.id,
            event_b_id=str(uuid.uuid4()),
            description="Conflict over database: PostgreSQL proposed but SQLite also suggested",
            contradiction_type=ContradictionType.DECISION,
            is_cross_meeting=False,
            review_state="PENDING",
            confidence=0.89,
        )
        db.add(contradiction)
        await db.commit()

        print(" -> Test meeting environment seeded.")

        # -------------------------------------------------------------
        # STEP 2: Query Classification Test
        # -------------------------------------------------------------
        print("\n[STEP 2] Verifying Query Classification intents...")
        assert query_engine.classify_query("Who agreed to handle authentication?") == "ACTION_OWNER"
        assert query_engine.classify_query("What decisions were made about the framework?") == "DECISION_STATUS"
        assert query_engine.classify_query("Were there any disagreements or conflicts?") == "CONTRADICTION"
        assert query_engine.classify_query("What is WASAPI?") == "FACTUAL"
        assert query_engine.classify_query("When was the mark moment flagged?") == "TIMELINE"
        print(" -> All 5 query classification patterns verified.")

        # -------------------------------------------------------------
        # STEP 3: Action Owner Query ("Who agreed to handle authentication?")
        # -------------------------------------------------------------
        print("\n[STEP 3] Testing Action Item Query: 'Who agreed to handle authentication?'...")
        ans1 = await query_engine.query(db=db, query_text="Who agreed to handle authentication?", meeting_id=m_id)
        print(f" -> Answer: {ans1.answer}")
        print(f" -> Confidence: {ans1.confidence}, Grounded: {ans1.grounded}")
        assert ans1.grounded is True
        assert ans1.confidence >= 0.85
        assert len(ans1.sources) >= 1
        assert any("Akhilesh" in s.quote or s.source_type == "ACTION_ITEM" for s in ans1.sources)
        print(f" -> Top source cited: [{ans1.sources[0].source_type}] '{ans1.sources[0].quote}'")

        # -------------------------------------------------------------
        # STEP 4: Decision Status Query ("What decisions were made?")
        # -------------------------------------------------------------
        print("\n[STEP 4] Testing Decision Query: 'What framework decisions were made?'...")
        ans2 = await query_engine.query(db=db, query_text="What framework decisions were made?", meeting_id=m_id)
        print(f" -> Answer: {ans2.answer}")
        assert ans2.grounded is True
        assert any(s.source_type == "DECISION" for s in ans2.sources)
        assert any("FastAPI" in s.quote for s in ans2.sources)
        print(" -> Verified decision grounded citation.")

        # -------------------------------------------------------------
        # STEP 5: Contradiction / Conflict Query
        # -------------------------------------------------------------
        print("\n[STEP 5] Testing Contradiction Query: 'Were there any disagreements or conflicts?'...")
        ans3 = await query_engine.query(db=db, query_text="Were there any disagreements or conflicts?", meeting_id=m_id)
        print(f" -> Answer: {ans3.answer}")
        assert ans3.grounded is True
        assert any(s.source_type == "CONTRADICTION" for s in ans3.sources)
        assert "Conflict over database" in ans3.answer or "Conflict" in ans3.sources[0].quote
        print(" -> Verified contradiction grounded citation.")

        # -------------------------------------------------------------
        # STEP 6: STRICT INVARIANT — Ungrounded query MUST NOT hallucinate
        # -------------------------------------------------------------
        print("\n[STEP 6] Testing Strict Invariant: Query with no evidence...")
        ungrounded_query = "Did we discuss quantum teleportation algorithms on Mars?"
        ans4 = await query_engine.query(db=db, query_text=ungrounded_query, meeting_id=m_id)
        print(f" -> Ungrounded response: {ans4.answer}")
        assert ans4.grounded is False
        assert ans4.confidence == 0.0
        assert len(ans4.sources) == 0
        assert "No supporting evidence" in ans4.answer
        print(" -> STRICT INVARIANT CONFIRMED: 0.0 confidence, grounded=False, no hallucinated prose.")

        # -------------------------------------------------------------
        # STEP 7: API Endpoint Verification (ask_meeting & ask_single_meeting)
        # -------------------------------------------------------------
        print("\n[STEP 7] Verifying FastAPI route endpoints...")
        api_resp = await ask_single_meeting(
            meeting_id=m_id,
            body={"query": "Who agreed to handle authentication?"},
            db=db,
        )
        assert api_resp["grounded"] is True
        assert api_resp["confidence"] >= 0.85
        assert len(api_resp["sources"]) >= 1

        org_resp = await ask_meeting(
            body={"query": "What decisions were made?", "meeting_id": None},
            db=db,
        )
        assert org_resp["grounded"] is True
        assert len(org_resp["sources"]) >= 1
        print(" -> API endpoints /api/query and /api/query/meeting/{id} verified.")

    print("\n======================================================================")
    print("ALL PHASE 7 AUTOMATED TESTS PASSED CLEANLY!")
    print("======================================================================")


if __name__ == "__main__":
    asyncio.run(run_phase7_tests())
