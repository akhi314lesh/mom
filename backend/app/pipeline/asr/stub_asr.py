"""
pipeline/asr/stub_asr.py — StubASRAdapter.

Returns a realistic pre-defined transcript.
Enables full pipeline and UI development without installing torch/whisper.
"""
from pathlib import Path

from app.pipeline.asr.asr_adapter import ASRAdapter, ASRResult, ASRSegment


_MOCK_SEGMENTS = [
    ASRSegment(start_ms=0, end_ms=8000, text="Alright, let's get started. Today we're discussing the backend architecture.", confidence=0.96),
    ASRSegment(start_ms=8500, end_ms=18000, text="I think we should use FastAPI. It's async, well-documented, and the team is familiar with it.", confidence=0.94),
    ASRSegment(start_ms=18500, end_ms=28000, text="I agree. And for the database, let's go with PostgreSQL. It fits our relational data model well.", confidence=0.92),
    ASRSegment(start_ms=28500, end_ms=40000, text="So we're going with FastAPI and PostgreSQL then? Everyone on board?", confidence=0.95),
    ASRSegment(start_ms=40500, end_ms=48000, text="Yes, sounds good to me.", confidence=0.97),
    ASRSegment(start_ms=48500, end_ms=58000, text="Agreed. I'll handle the FastAPI project scaffold. Should be done by next Friday.", confidence=0.93),
    ASRSegment(start_ms=58500, end_ms=70000, text="And Priya, can you take a look at the database schema? We need to finalize the entity model.", confidence=0.91),
    ASRSegment(start_ms=70500, end_ms=82000, text="Sure, I can work on that. No specific deadline?", confidence=0.90),
    ASRSegment(start_ms=82500, end_ms=94000, text="Let's say end of next week as well. Also, should we use Redis for session management? I'm not sure yet.", confidence=0.88),
    ASRSegment(start_ms=94500, end_ms=105000, text="That's a good question. Let's leave that open for now and decide once we have more info on load requirements.", confidence=0.89),
]


class StubASRAdapter(ASRAdapter):
    """
    Stub ASR adapter returning deterministic realistic transcript.
    Use when ASR_PROVIDER=stub (default for development).
    """

    async def transcribe(self, audio_path: Path, language: str | None = None) -> ASRResult:
        """Return mock transcript regardless of input file."""
        return ASRResult(
            segments=_MOCK_SEGMENTS,
            language=language or "en",
            duration_ms=105000,
            model_used="stub",
            adapter_used="StubASRAdapter",
        )

    def is_available(self) -> bool:
        return True
