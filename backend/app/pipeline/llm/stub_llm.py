"""
pipeline/llm/stub_llm.py — StubLLMAdapter.

Returns realistic deterministic mock data.
Enables full system development and testing without any API keys.

The stub produces mock semantic extractions that exercise the full pipeline.
"""
import json
from typing import Any, TypeVar

from pydantic import BaseModel

from app.pipeline.llm.llm_adapter import LLMAdapter

T = TypeVar("T", bound=BaseModel)

_MOCK_TRANSCRIPT_ANALYSIS = {
    "decisions": [
        {
            "text": "Use FastAPI for the backend framework",
            "confidence": 0.92,
            "evidence_quote": "Let's use FastAPI — it's async and well-suited for this.",
        },
        {
            "text": "PostgreSQL as the primary database",
            "confidence": 0.88,
            "evidence_quote": "PostgreSQL makes sense given our data model.",
        },
    ],
    "action_items": [
        {
            "task": "Set up FastAPI project scaffold",
            "owner": "Akhilesh",
            "deadline": "2026-10-11",
            "confidence": 0.95,
            "evidence_quote": "I'll handle the backend setup by next Friday.",
        },
        {
            "task": "Design the database schema",
            "owner": "Priya",
            "deadline": None,
            "confidence": 0.81,
            "evidence_quote": "Priya, can you take a look at the schema?",
        },
    ],
    "questions": [
        {
            "text": "Should we use Redis for session management?",
            "answered": False,
            "confidence": 0.90,
        }
    ],
    "topics": [
        {"title": "Backend architecture", "start_ms": 60000, "end_ms": 900000},
        {"title": "Database selection", "start_ms": 900000, "end_ms": 1800000},
    ],
    "summary": (
        "The team discussed backend architecture choices, settling on FastAPI and PostgreSQL. "
        "Akhilesh will set up the project scaffold. Priya will review the database schema. "
        "Redis for session management remains an open question."
    ),
}


class StubLLMAdapter(LLMAdapter):
    """
    Stub LLM adapter that returns deterministic mock data.
    Use when LLM_PROVIDER=stub (default for development).
    """

    async def complete(self, prompt: str, system: str = "", **kwargs: Any) -> str:
        """Return a mock completion based on the prompt content."""
        if "summary" in prompt.lower():
            return _MOCK_TRANSCRIPT_ANALYSIS["summary"]
        if "decision" in prompt.lower():
            return json.dumps(_MOCK_TRANSCRIPT_ANALYSIS["decisions"])
        if "action" in prompt.lower():
            return json.dumps(_MOCK_TRANSCRIPT_ANALYSIS["action_items"])
        return "Mock LLM response for: " + prompt[:100]

    async def extract_structured(
        self,
        prompt: str,
        schema: type[T],
        system: str = "",
        **kwargs: Any,
    ) -> T:
        """Return a mock structured extraction. Attempts to build a minimal valid schema."""
        try:
            # Try to build with empty/default values
            instance = schema.model_validate({})
            return instance
        except Exception:
            # If that fails, try with the full mock data
            try:
                return schema.model_validate(_MOCK_TRANSCRIPT_ANALYSIS)
            except Exception:
                raise ValueError(
                    f"StubLLMAdapter cannot auto-build schema {schema.__name__}. "
                    "Provide explicit mock data for this schema."
                )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Stub adapter is free."""
        return 0.0
