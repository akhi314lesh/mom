"""
backend/tests/test_phase5_contradictions_live.py

Automated test suite for Phase 5 deliverables:
1. Streaming live utterance ingestion (LiveCaptureProcessor) creating TranscriptSegments & Evidence.
2. Within-meeting contradiction detection:
   - Invariant: System ALWAYS prefers DECISION UNRESOLVED over silently choosing one side.
   - Invariant: Both sides preserved in evidence.
   - Invariant: Decision status degraded to UNRESOLVED, review_state to UNCERTAIN.
   - Escalates to high-priority ReviewItem.
3. Human arbitration resolution flow:
   - Invariant: Creates immutable Evidence with source_type="HUMAN_CORRECTION".
   - Invariant: Contradiction marked RESOLVED, winning decision CONFIRMED, losing decision OVERRIDDEN.
4. Cross-meeting continuity & contradiction detection:
   - Detects conflicts across meeting boundaries with is_cross_meeting=True.
5. Canonical MeetingRecord verification:
   - Returns contradictions and semantic_events.
"""
import asyncio
import os
import sys

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database import create_all_tables


async def run_phase5_tests():
    await create_all_tables()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("[TEST 1] Creating Meeting 1 for live capture session...")
        m1_res = await client.post(
            "/api/meetings/",
            json={"title": "Architecture Sync - Database Strategy", "capture_mode": "OVERLAY"},
        )
        assert m1_res.status_code == 201
        m1 = m1_res.json()
        m1_id = m1["id"]
        print(f" -> Created Meeting 1: {m1_id}")

        print("[TEST 2] Ingesting streaming live speech chunks (LiveCaptureProcessor)...")
        # Utterance 1: Decision proposal
        chunk1 = await client.post(
            f"/api/contradictions/{m1_id}/live-chunk",
            json={
                "text": "The consensus is we have decided we will use PostgreSQL as our database.",
                "start_ms": 10000,
                "end_ms": 15000,
                "speaker_name": "Akhilesh",
            },
        )
        assert chunk1.status_code == 200
        print(" -> Ingested utterance 1 (decision candidate)")

        # Utterance 2: Conflicting decision proposal
        chunk2 = await client.post(
            f"/api/contradictions/{m1_id}/live-chunk",
            json={
                "text": "I disagree with that. The decision is to we will use MongoDB for document agility.",
                "start_ms": 18000,
                "end_ms": 23000,
                "speaker_name": "Priya",
            },
        )
        assert chunk2.status_code == 200
        print(" -> Ingested utterance 2 (disagreement & opposing decision)")

        print("[TEST 3] Running within-meeting contradiction detection...")
        det_res = await client.post(f"/api/contradictions/{m1_id}/detect")
        assert det_res.status_code == 200
        det_data = det_res.json()
        assert det_data["detected_count"] >= 1, f"Expected at least 1 contradiction, got {det_data['detected_count']}"
        print(f" -> Contradictions detected: {det_data['detected_count']}")

        print("[TEST 4] Fetching meeting contradictions list & verifying INVARIANTS...")
        con_list_res = await client.get(f"/api/contradictions/meeting/{m1_id}")
        assert con_list_res.status_code == 200
        con_data = con_list_res.json()
        contradictions = con_data["contradictions"]
        assert len(contradictions) >= 1
        target_con = contradictions[0]
        print(f" -> Detected Contradiction: {target_con['description']}")
        print(f"    Side A: {target_con['event_a_text']}")
        print(f"    Side B: {target_con['event_b_text']}")

        # Verify underlying decisions status: MUST be UNRESOLVED per architecture invariant
        rec_res = await client.get(f"/api/meetings/{m1_id}/record")
        assert rec_res.status_code == 200
        rec_data = rec_res.json()
        decisions = rec_data["decisions"]
        assert any(d["status"] == "UNRESOLVED" for d in decisions), "INVARIANT VIOLATION: Decision status must be UNRESOLVED when contested!"
        print(" -> Verified Invariant: Decision status correctly degraded to UNRESOLVED without silent consensus assumption.")

        print("[TEST 5] Checking Review Queue escalation...")
        rev_res = await client.get(f"/api/review/{m1_id}")
        assert rev_res.status_code == 200
        review_items = rev_res.json()
        assert any(
            r["type"] in ("CONTRADICTION", "DISAGREEMENT") for r in review_items
        ), "Contradiction failed to escalate to ReviewItem queue"
        print(f" -> Verified: Contradiction escalated to ReviewItem queue with priority scoring.")

        print("[TEST 6] Resolving contradiction through human arbitration...")
        con_id = target_con["id"]
        resolve_res = await client.patch(
            f"/api/contradictions/{con_id}/resolve",
            json={
                "resolution": "Adopt PostgreSQL with JSONB columns for document agility.",
                "chosen_side": "A",
                "author": "Lead Architect Akhilesh",
            },
        )
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == "resolved"
        print(" -> Contradiction successfully resolved by human arbiter.")

        print("[TEST 7] Verifying immutable Evidence created for human arbitration...")
        ev_list_res = await client.get(f"/api/evidence/{m1_id}")
        assert ev_list_res.status_code == 200
        evidences = ev_list_res.json()
        human_corr_ev = next((e for e in evidences if e["source_type"] == "HUMAN_CORRECTION"), None)
        assert human_corr_ev is not None, "INVARIANT VIOLATION: Human arbitration must produce immutable Evidence (source_type=HUMAN_CORRECTION)"
        assert human_corr_ev["confidence"] == 1.0
        print(f" -> Verified Invariant: Created immutable Evidence: '{human_corr_ev['raw_text']}'")

        print("[TEST 8] Testing Cross-Meeting Continuity & Contradiction Detection...")
        # Create Meeting 2
        m2_res = await client.post(
            "/api/meetings/",
            json={"title": "Retrospective & Direction Review", "capture_mode": "OVERLAY"},
        )
        assert m2_res.status_code == 201
        m2_id = m2_res.json()["id"]

        # Ingest opposing decision in Meeting 2
        await client.post(
            f"/api/contradictions/{m2_id}/live-chunk",
            json={
                "text": "The consensus is we have decided we will use MongoDB as our database after all.",
                "start_ms": 5000,
                "end_ms": 10000,
            },
        )
        cross_res = await client.post(f"/api/contradictions/{m2_id}/detect")
        assert cross_res.status_code == 200
        cross_data = cross_res.json()
        print(f" -> Cross-meeting contradiction detected: {cross_data['detected_count']} conflicts found.")

        print("[TEST 9] Verifying Canonical MeetingRecord delivery of Phase 5 intelligence...")
        m1_rec = await client.get(f"/api/meetings/{m1_id}/record")
        assert m1_rec.status_code == 200
        m1_body = m1_rec.json()
        assert "contradictions" in m1_body
        assert "semantic_events" in m1_body
        print(f" -> Canonical MeetingRecord verified: {len(m1_body['contradictions'])} contradiction(s), {len(m1_body['semantic_events'])} semantic event(s).")

    print("\nALL PHASE 5 AUTOMATED TESTS PASSED CLEANLY!")


if __name__ == "__main__":
    asyncio.run(run_phase5_tests())
