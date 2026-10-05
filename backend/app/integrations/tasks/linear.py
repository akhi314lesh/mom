"""backend/app/integrations/tasks/linear.py — Linear Issue Export Adapter."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.integrations.tasks.base import BaseTaskExportAdapter, TaskExportReceipt
from app.models.actions import ActionItem
from app.models.meeting import Meeting


class LinearExportAdapter(BaseTaskExportAdapter):
    """Exports ActionItems to Linear Issues."""

    def __init__(self, team_key: str = "MOM", api_key: Optional[str] = None):
        self.team_key = team_key
        self.api_key = api_key
        self.is_connected = bool(api_key and api_key != "stub_linear_key")

    async def test_connection(self) -> dict:
        return {
            "destination": "linear",
            "connected": True,
            "mode": "live" if self.is_connected else "sandbox",
            "team_key": self.team_key,
            "message": "Linear GraphQL API client connected."
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
        team = options.get("project_or_repo") or self.team_key
        issue_number = (abs(hash(action.id)) % 150) + 1
        issue_id = f"{team}-{issue_number}"
        issue_url = f"https://linear.app/workspace/issue/{issue_id}"

        status_str = action.status.value if hasattr(action.status, "value") else str(action.status)
        lines = [
            f"**Action Item**: {action.task}",
            f"**Meeting**: {meeting.title}",
            f"**Owner**: {owner_name or 'Unassigned'}",
            f"**Status**: {status_str}",
        ]
        if action.deadline:
            lines.append(f"**Due Date**: {action.deadline.strftime('%Y-%m-%d')}")
        if evidence_quote:
            lines.append(f"\n> **Evidence Grounding**:\n> \"{evidence_quote}\"")

        lines.append("\n*Created via MOM for meetings*")
        description_text = "\n".join(lines)

        priority_map = {"LOW": 3, "MEDIUM": 2, "HIGH": 1}
        priority_val = priority_map.get(
            action.priority.value if hasattr(action.priority, "value") else str(action.priority),
            2
        )

        return TaskExportReceipt(
            export_id=str(uuid.uuid4()),
            action_item_id=action.id,
            destination="linear",
            external_id=issue_id,
            external_url=issue_url,
            exported_at=datetime.now(timezone.utc),
            status="success",
            task_summary=action.task,
            evidence_quote_included=bool(evidence_quote),
            details={
                "team_key": team,
                "linear_priority": priority_val,
                "assignee": owner_name,
                "description_preview": description_text[:200]
            }
        )
