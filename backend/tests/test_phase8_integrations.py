"""backend/tests/test_phase8_integrations.py — Phase 8 automated integration test suite."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.database import AsyncSessionLocal, create_all_tables
from app.models.meeting import Meeting, CaptureMode, MeetingLifecycle, ProcessingStatus, PrivacyMode
from app.models.participant import Participant
from app.models.actions import ActionItem, ActionItemStatus, ActionItemPriority
from app.models.evidence import Evidence
from app.models.questions import Question
from app.models.brief import MeetingBrief
from app.integrations.manager import integration_manager
from app.integrations.calendar.google_calendar import GoogleCalendarAdapter
from app.integrations.calendar.outlook_calendar import OutlookCalendarAdapter
from app.integrations.calendar.brief_generator import brief_generator
from app.integrations.tasks.jira import JiraExportAdapter
from app.integrations.tasks.github_issues import GitHubIssuesExportAdapter
from app.integrations.tasks.linear import LinearExportAdapter
from app.api.integrations import (
    get_settings,
    update_settings,
    test_provider,
    list_calendar_events,
    import_calendar_meeting,
    export_task,
    get_meeting_brief,
    regenerate_meeting_brief,
    ImportMeetingRequest,
)
from app.integrations.tasks.base import TaskExportRequest


async def run_phase8_tests():
    print("\n" + "=" * 70)
    print("PHASE 8 AUTOMATED TEST SUITE: EXTERNAL INTEGRATIONS + MEETING BRIEFS")
    print("=" * 70)

    await create_all_tables()

    # STEP 1: Test Calendar Adapters
    print("\n[STEP 1] Testing Google & Outlook Calendar Adapters...")
    gcal = GoogleCalendarAdapter()
    g_conn = await gcal.test_connection()
    assert g_conn["connected"] is True
    assert g_conn["provider"] == "google"

    g_events = await gcal.get_upcoming_events()
    assert len(g_events) >= 2, "Google calendar should return upcoming sprint events"
    ev1 = g_events[0]
    assert "Sprint" in ev1.title
    assert len(ev1.attendees) > 0
    print(f" -> Google Calendar: {len(g_events)} events found. Sample: '{ev1.title}'")

    ocal = OutlookCalendarAdapter()
    o_conn = await ocal.test_connection()
    assert o_conn["connected"] is True
    assert o_conn["provider"] == "outlook"

    o_events = await ocal.get_upcoming_events()
    assert len(o_events) >= 1, "Outlook calendar should return upcoming sync events"
    print(f" -> Outlook Calendar: {len(o_events)} events found. Sample: '{o_events[0].title}'")

    # STEP 2: Test Central Integration Manager Settings & Connections
    print("\n[STEP 2] Testing IntegrationManager provider test matrix...")
    for prov in ["google", "outlook", "jira", "github", "linear"]:
        res = await integration_manager.test_connection(prov)
        assert res["connected"] is True, f"Provider {prov} should connect"
        print(f" -> Provider '{prov}' connection verified: {res.get('message')}")

    settings = integration_manager.get_settings()
    assert "google_calendar" in settings
    assert "jira" in settings
    assert "github" in settings

    integration_manager.update_settings({"github": {"default_labels": ["meeting-action", "priority"]}})
    updated = integration_manager.get_settings()
    assert "priority" in updated["github"]["default_labels"]
    print(" -> IntegrationManager settings update verified.")

    # STEP 3: Setup Prior Context for Meeting Brief Auto-Generation
    print("\n[STEP 3] Setting up prior meeting data to test pre-meeting brief generation...")
    async with AsyncSessionLocal() as db:
        prior_m_id = str(uuid.uuid4())
        prior_meeting = Meeting(
            id=prior_m_id,
            title="Backend Sprint Architecture Sync",
            date=datetime.now(timezone.utc) - timedelta(days=2),
            capture_mode=CaptureMode.IMPORT,
            lifecycle_status=MeetingLifecycle.FINALIZED,
            processing_status=ProcessingStatus.COMPLETE,
            privacy_mode=PrivacyMode.LOCAL,
            description="Discussed microservices and JWT token auth.",
            quality_metrics={},
        )
        db.add(prior_meeting)

        p1 = Participant(
            id=str(uuid.uuid4()),
            meeting_id=prior_m_id,
            name="Akhilesh",
            email="akhilesh@example.com",
            role="LEAD",
            is_self=True,
        )
        p2 = Participant(
            id=str(uuid.uuid4()),
            meeting_id=prior_m_id,
            name="Bob",
            email="bob@example.com",
            role="ENGINEER",
            is_self=False,
        )
        db.add_all([p1, p2])

        # Prior Action Item (still pending)
        prior_action = ActionItem(
            id=str(uuid.uuid4()),
            originating_meeting_id=prior_m_id,
            originating_timestamp_ms=120000,
            task="Refactor JWT token expiry and refresh flow",
            owner_id=p1.id,
            owner_confidence=0.95,
            deadline=datetime.now(timezone.utc) + timedelta(days=3),
            deadline_confidence=0.90,
            status=ActionItemStatus.PENDING,
            priority=ActionItemPriority.HIGH,
            evidence_ids=[],
            confidence=0.96,
        )
        db.add(prior_action)

        # Prior Unresolved Question
        prior_q = Question(
            id=str(uuid.uuid4()),
            meeting_id=prior_m_id,
            text="Should we use Redis or PostgreSQL for session revocation?",
            answered=False,
            confidence=0.88,
        )
        db.add(prior_q)

        # Evidence for action item export
        ev_id = str(uuid.uuid4())
        ev = Evidence(
            id=ev_id,
            meeting_id=prior_m_id,
            source_type="TRANSCRIPT_SEGMENT",
            raw_text="Akhilesh agreed: 'I will refactor the JWT token expiry flow by Wednesday.'",
            confidence=0.98,
            is_immutable=True,
        )
        db.add(ev)
        prior_action.evidence_ids = [ev_id]

        await db.commit()
        print(" -> Prior meeting, participants, open action item, and evidence committed.")

    # STEP 4: Test Calendar Event Import & Brief Generation via API
    print("\n[STEP 4] Testing Calendar Meeting Import and MeetingBrief Auto-Generation...")
    async with AsyncSessionLocal() as db:
        import_req = ImportMeetingRequest(
            event_id="gcal-event-eng-sprint-101",
            auto_generate_brief=True
        )
        import_resp = await import_calendar_meeting(import_req, db)
        assert import_resp["status"] == "imported"
        new_m = import_resp["meeting"]
        brief_data = import_resp["brief"]

        assert new_m["title"] == "Sprint Planning: Mobile Architecture & Offline Sync"
        assert brief_data is not None, "MeetingBrief must be generated upon calendar import"
        assert prior_m_id in brief_data["previous_meeting_ids"], "Brief must discover prior related meeting"
        assert prior_action.id in brief_data["open_action_item_ids"], "Brief must carry forward open action item"
        assert prior_q.id in brief_data["unresolved_question_ids"], "Brief must track unresolved question"
        assert len(brief_data["expected_topics"]) > 0, "Brief must extract expected agenda topics"
        print(f" -> Meeting '{new_m['title']}' created with briefing ID '{new_m['briefing_id']}'")
        print(f"    Expected Topics: {brief_data['expected_topics']}")
        print(f"    Carried Action Items: {len(brief_data['open_action_item_ids'])}")
        print(f"    Linked Prior Meetings: {len(brief_data['previous_meeting_ids'])}")

        # Verify get_meeting_brief API endpoint
        enriched_brief = await get_meeting_brief(new_m["id"], db)
        assert len(enriched_brief["previous_meetings"]) > 0
        assert len(enriched_brief["open_action_items"]) > 0
        print(" -> Enriched MeetingBrief endpoint successfully verified.")

    # STEP 5: Test Task Export to Jira, GitHub Issues, and Linear
    print("\n[STEP 5] Testing Action Item Export Adapters (Jira, GitHub Issues, Linear)...")
    async with AsyncSessionLocal() as db:
        # Jira Export
        jira_req = TaskExportRequest(
            action_item_id=prior_action.id,
            destination="jira",
            project_or_repo="MOM"
        )
        jira_receipt = await export_task(jira_req, db)
        assert jira_receipt.destination == "jira"
        assert jira_receipt.external_id.startswith("MOM-")
        assert "browse" in jira_receipt.external_url
        assert jira_receipt.evidence_quote_included is True
        print(f" -> Jira Export OK: Issue {jira_receipt.external_id} -> {jira_receipt.external_url}")

        # GitHub Issues Export
        gh_req = TaskExportRequest(
            action_item_id=prior_action.id,
            destination="github",
            project_or_repo="akhi314lesh/mom",
            labels=["action-item", "backend"]
        )
        gh_receipt = await export_task(gh_req, db)
        assert gh_receipt.destination == "github"
        assert gh_receipt.external_id.startswith("#")
        assert "github.com/akhi314lesh/mom/issues/" in gh_receipt.external_url
        assert gh_receipt.evidence_quote_included is True
        print(f" -> GitHub Export OK: Issue {gh_receipt.external_id} -> {gh_receipt.external_url}")

        # Linear Export
        lin_req = TaskExportRequest(
            action_item_id=prior_action.id,
            destination="linear",
            project_or_repo="MOM"
        )
        lin_receipt = await export_task(lin_req, db)
        assert lin_receipt.destination == "linear"
        assert lin_receipt.external_id.startswith("MOM-")
        assert "linear.app" in lin_receipt.external_url
        assert lin_receipt.evidence_quote_included is True
        print(f" -> Linear Export OK: Issue {lin_receipt.external_id} -> {lin_receipt.external_url}")

    # STEP 6: Verify API Settings & Calendar Events
    print("\n[STEP 6] Verifying API Integration Settings & Calendar Events list...")
    cur_settings = await get_settings()
    assert cur_settings["google_calendar"]["enabled"] is True
    assert cur_settings["github"]["repository"] == "akhi314lesh/mom"

    cal_events = await list_calendar_events()
    assert len(cal_events) >= 3, "Should aggregate events from active calendar providers"
    print(f" -> Aggregated {len(cal_events)} calendar events successfully.")

    print("\n" + "=" * 70)
    print("ALL PHASE 8 AUTOMATED TESTS PASSED CLEANLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_phase8_tests())
