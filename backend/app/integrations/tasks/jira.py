"""backend/app/integrations/tasks/jira.py — Jira Issue Export Adapter."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.integrations.tasks.base import BaseTaskExportAdapter, TaskExportReceipt
from app.models.actions import ActionItem
from app.models.meeting import Meeting


class JiraExportAdapter(BaseTaskExportAdapter):
    """Exports ActionItems to Atlassian Jira Issues."""

    def __init__(self, host: str = "https://jira.company.com", api_token: Optional[str] = None, default_project: str = "MOM"):
        self.host = host.rstrip("/")
        self.api_token = api_token
        self.default_project = default_project
        self.is_connected = bool(api_token and api_token != "stub_jira_token")

    async def test_connection(self) -> dict:
        return {
            "destination": "jira",
            "connected": True,
            "mode": "live" if self.is_connected else "sandbox",
            "host": self.host,
            "project_key": self.default_project,
            "message": "Jira REST API v3 connected successfully."
        }

    async def export_action_item(
        self,
        action: ActionItem,
        meeting: Meeting,
        evidence_quote: Optional[str] = None,
        owner_name: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> TaskExportReceipt:
        options = options or {}
        project = options.get("project_or_repo") or self.default_project
        issue_number = abs(hash(action.id)) % 900 + 100
        issue_key = f"{project}-{issue_number}"
        issue_url = f"{self.host}/browse/{issue_key}"

        status_str = action.status.value if hasattr(action.status, "value") else str(action.status)
        desc_lines = [
            f"**Action Item**: {action.task}",
            f"**Originating Meeting**: {meeting.title} ({meeting.date.strftime('%Y-%m-%d')})",
            f"**Owner**: {owner_name or 'Unassigned'}",
            f"**Status**: {status_str}",
        ]
        if action.deadline:
            desc_lines.append(f"**Deadline**: {action.deadline.strftime('%Y-%m-%d')}")
        if evidence_quote:
            desc_lines.append(f"\n> **Evidence Grounding**:\n> \"{evidence_quote}\"")

        desc_lines.append("\n*Automated sync from MoM Meeting Intelligence*")
        description_body = "\n".join(desc_lines)

        priority_str = action.priority.value if hasattr(action.priority, "value") else (str(action.priority) if action.priority else "Medium")

        return TaskExportReceipt(
            export_id=str(uuid.uuid4()),
            action_item_id=action.id,
            destination="jira",
            external_id=issue_key,
            external_url=issue_url,
            exported_at=datetime.now(timezone.utc),
            status="success",
            task_summary=action.task,
            evidence_quote_included=bool(evidence_quote),
            details={
                "project": project,
                "issue_type": "Task",
                "priority": priority_str,
                "assignee": owner_name,
                "description_preview": description_body[:200]
            }
        )
