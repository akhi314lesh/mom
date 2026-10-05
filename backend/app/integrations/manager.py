"""backend/app/integrations/manager.py — Central Integration Manager."""
from typing import Dict, Any, List, Optional
from app.integrations.calendar.base import CalendarEvent
from app.integrations.calendar.google_calendar import GoogleCalendarAdapter
from app.integrations.calendar.outlook_calendar import OutlookCalendarAdapter
from app.integrations.tasks.base import TaskExportReceipt
from app.integrations.tasks.jira import JiraExportAdapter
from app.integrations.tasks.github_issues import GitHubIssuesExportAdapter
from app.integrations.tasks.linear import LinearExportAdapter
from app.models.actions import ActionItem
from app.models.meeting import Meeting


class IntegrationManager:
    """Coordinates calendar adapters and task export targets."""

    def __init__(self):
        # Default configurations
        self.settings: Dict[str, Any] = {
            "google_calendar": {
                "enabled": True,
                "api_key": "stub_google_key",
                "calendar_id": "primary",
                "auto_sync_interval_mins": 30,
                "auto_generate_briefs": True,
            },
            "outlook_calendar": {
                "enabled": True,
                "client_id": "stub_outlook_client",
                "tenant_id": "common",
                "auto_sync_interval_mins": 60,
                "auto_generate_briefs": True,
            },
            "jira": {
                "enabled": True,
                "host": "https://jira.company.com",
                "api_token": "stub_jira_token",
                "default_project": "MOM",
            },
            "github": {
                "enabled": True,
                "repository": "akhi314lesh/mom",
                "github_token": "stub_gh_token",
                "default_labels": ["action-item", "meeting-intelligence"],
            },
            "linear": {
                "enabled": True,
                "team_key": "MOM",
                "api_key": "stub_linear_key",
            },
        }

        self._init_adapters()

    def _init_adapters(self):
        self.google_calendar = GoogleCalendarAdapter(
            api_key=self.settings["google_calendar"]["api_key"],
            calendar_id=self.settings["google_calendar"]["calendar_id"]
        )
        self.outlook_calendar = OutlookCalendarAdapter(
            client_id=self.settings["outlook_calendar"]["client_id"],
            tenant_id=self.settings["outlook_calendar"]["tenant_id"]
        )
        self.jira = JiraExportAdapter(
            host=self.settings["jira"]["host"],
            api_token=self.settings["jira"]["api_token"],
            default_project=self.settings["jira"]["default_project"]
        )
        self.github = GitHubIssuesExportAdapter(
            default_repo=self.settings["github"]["repository"],
            github_token=self.settings["github"]["github_token"]
        )
        self.linear = LinearExportAdapter(
            team_key=self.settings["linear"]["team_key"],
            api_key=self.settings["linear"]["api_key"]
        )

    def get_settings(self) -> Dict[str, Any]:
        return self.settings

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in updates.items():
            if k in self.settings and isinstance(v, dict):
                self.settings[k].update(v)
            elif k in self.settings:
                self.settings[k] = v
        self._init_adapters()
        return self.settings

    async def test_connection(self, provider: str) -> Dict[str, Any]:
        p = provider.lower()
        if p in ("google", "google_calendar"):
            return await self.google_calendar.test_connection()
        elif p in ("outlook", "outlook_calendar", "microsoft"):
            return await self.outlook_calendar.test_connection()
        elif p == "jira":
            return await self.jira.test_connection()
        elif p in ("github", "github_issues"):
            return await self.github.test_connection()
        elif p == "linear":
            return await self.linear.test_connection()
        else:
            raise ValueError(f"Unknown integration provider: {provider}")

    async def get_upcoming_events(self) -> List[CalendarEvent]:
        events: List[CalendarEvent] = []
        if self.settings["google_calendar"].get("enabled", True):
            g_events = await self.google_calendar.get_upcoming_events()
            events.extend(g_events)
        if self.settings["outlook_calendar"].get("enabled", True):
            o_events = await self.outlook_calendar.get_upcoming_events()
            events.extend(o_events)

        events.sort(key=lambda e: e.start_time)
        return events

    async def export_action_item(
        self,
        action: ActionItem,
        meeting: Meeting,
        destination: str,
        evidence_quote: Optional[str] = None,
        owner_name: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> TaskExportReceipt:
        dest = destination.lower()
        if dest == "jira":
            return await self.jira.export_action_item(action, meeting, evidence_quote, owner_name, options)
        elif dest in ("github", "github_issues"):
            return await self.github.export_action_item(action, meeting, evidence_quote, owner_name, options)
        elif dest == "linear":
            return await self.linear.export_action_item(action, meeting, evidence_quote, owner_name, options)
        else:
            raise ValueError(f"Unsupported export destination: {destination}")


integration_manager = IntegrationManager()
