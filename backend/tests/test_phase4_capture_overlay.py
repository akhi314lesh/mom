"""
backend/tests/test_phase4_capture_overlay.py

Automated test suite for Phase 4 deliverables:
1. Capture session initialization and AudioSourceState detection.
2. Graceful degradation: audio failure falls back to NO_AUDIO without crashing.
3. UserMark creation via Mark Moment (Ctrl+Shift+M):
   - Invariant: source is always 'HUMAN'
   - Invariant: processing_priority = 1.0
   - Invariant: creates immutable Evidence record with confidence=1.0
4. Manual capture resilience: marks succeed even in degraded audio mode.
5. Canonical MeetingRecord includes user_marks.
"""
import asyncio
import os
import sys

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database import create_all_tables


async def run_phase4_tests():
    await create_all_tables()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("[TEST 1] Creating a test meeting...")
        m_res = await client.post("/api/meetings/", json={"title": "Sprint Planning Live Sync", "capture_mode": "OVERLAY"})
        assert m_res.status_code == 201, f"Failed to create meeting: {m_res.text}"
        meeting_data = m_res.json()
        meeting_id = meeting_data["id"]
        print(f" -> Created meeting: {meeting_id}")

        print("[TEST 2] Starting capture session (Phase 4)...")
        cap_res = await client.post("/api/capture/session/start", json={"meeting_id": meeting_id, "capture_mode": "OVERLAY"})
        assert cap_res.status_code == 200, f"Failed to start capture session: {cap_res.text}"
        cap_data = cap_res.json()
        session_id = cap_data["session_id"]
        audio_state = cap_data["audio_source_state"]
        print(f" -> Capture session started: {session_id}, AudioSourceState: {audio_state}")
        assert "evidence_manifest" in cap_data
        assert "MANUAL_MARKS" in cap_data["evidence_manifest"]["available_sources"]

        print("[TEST 3] Fetching capture session status...")
        sess_res = await client.get(f"/api/capture/{meeting_id}/session")
        assert sess_res.status_code == 200
        sess_info = sess_res.json()["session"]
        assert sess_info["is_active"] is True
        assert len(sess_info["sources"]) == 3  # mic, sys, manual
        print(f" -> Active sources verified: {[s['source_type'] for s in sess_info['sources']]}")

        print("[TEST 4] Creating Mark Moment (UserMark) via Ctrl+Shift+M simulation...")
        mark_res = await client.post(
            f"/api/capture/{meeting_id}/mark",
            json={
                "event_type": "DECISION",
                "text": "Team agreed to deploy v1.2 to staging on Thursday",
                "priority": 1.0,
            },
        )
        assert mark_res.status_code == 200, f"Mark moment failed: {mark_res.text}"
        mark_data = mark_res.json()
        assert mark_data["success"] is True
        mark = mark_data["mark"]
        assert mark["source"] == "HUMAN", "INVARIANT VIOLATION: UserMark source must be HUMAN"
        assert mark["processing_priority"] == 1.0, "INVARIANT VIOLATION: UserMark processing_priority must be 1.0"
        evidence_id = mark_data["evidence_id"]
        print(f" -> UserMark created: id={mark['id']}, priority={mark['processing_priority']}, evidence_id={evidence_id}")

        print("[TEST 5] Verifying corresponding immutable Evidence record...")
        ev_res = await client.get(f"/api/evidence/{meeting_id}/item/{evidence_id}")
        assert ev_res.status_code == 200, f"Evidence lookup failed: {ev_res.text}"
        ev_data = ev_res.json()
        assert ev_data["source_type"] == "USER_MARK"
        assert ev_data["confidence"] == 1.0
        assert ev_data["is_immutable"] is True
        print(f" -> Evidence verified: type={ev_data['source_type']}, confidence={ev_data['confidence']}, immutable={ev_data['is_immutable']}")

        print("[TEST 6] Adding additional quick marks (Action, Flag, Note)...")
        for event_type, text in [
            ("ACTION", "Akhilesh to prepare release notes and migration script"),
            ("FLAG", "Potential blocker: DB migration might require 5 min downtime"),
            ("NOTE", "Reminder: notify customer success team 24h prior"),
        ]:
            res = await client.post(
                f"/api/capture/{meeting_id}/mark",
                json={"event_type": event_type, "text": text},
            )
            assert res.status_code == 200

        marks_list_res = await client.get(f"/api/capture/{meeting_id}/marks")
        assert marks_list_res.status_code == 200
        all_marks = marks_list_res.json()["marks"]
        assert len(all_marks) == 4, f"Expected 4 marks, got {len(all_marks)}"
        print(f" -> Successfully listed all {len(all_marks)} marks.")

        print("[TEST 7] Testing Graceful Degradation (Simulated mic disconnect)...")
        degrade_res = await client.post(
            f"/api/capture/{meeting_id}/simulate-toggle",
            json={"source": "mic", "force_fail": True},
        )
        assert degrade_res.status_code == 200
        degrade_data = degrade_res.json()
        print(f" -> Simulated mic disconnect: new AudioSourceState = {degrade_data['audio_source_state']}")
        assert degrade_data["audio_source_status"]["fallback_applied"] is True

        print("[TEST 8] Verifying Mark Moment STILL SUCCEEDS during audio hardware failure...")
        fail_mark_res = await client.post(
            f"/api/capture/{meeting_id}/mark",
            json={"event_type": "NOTE", "text": "Hardware audio failed, but manual mark works flawlessly!"},
        )
        assert fail_mark_res.status_code == 200
        assert fail_mark_res.json()["success"] is True
        print(" -> Verified: Manual mark captured without impediment under audio hardware failure!")

        print("[TEST 9] Verifying Canonical MeetingRecord includes user_marks...")
        rec_res = await client.get(f"/api/meetings/{meeting_id}/record")
        assert rec_res.status_code == 200
        rec_data = rec_res.json()
        assert "user_marks" in rec_data
        assert len(rec_data["user_marks"]) == 5
        print(f" -> Canonical MeetingRecord verified: contains {len(rec_data['user_marks'])} user_marks.")

        print("[TEST 10] Stopping capture session...")
        stop_res = await client.post(f"/api/capture/{meeting_id}/session/stop")
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] == "stopped"
        print(" -> Capture session cleanly stopped.")

    print("\nALL PHASE 4 BACKEND TESTS PASSED CLEANLY!")


if __name__ == "__main__":
    asyncio.run(run_phase4_tests())
