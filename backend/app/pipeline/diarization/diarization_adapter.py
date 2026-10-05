"""
pipeline/diarization/diarization_adapter.py — Abstract diarization interface.

ALL speaker diarization calls go through this interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiarizationSegment:
    """One speaker turn from diarization output."""
    speaker_label: str      # e.g. "SPEAKER_0", "SPEAKER_1"
    start_ms: int
    end_ms: int
    confidence: float = 0.0


@dataclass
class DiarizationResult:
    """Full diarization output for an audio file."""
    segments: list[DiarizationSegment] = field(default_factory=list)
    num_speakers: int = 0
    adapter_used: str = ""


class DiarizationAdapter(ABC):
    @abstractmethod
    async def diarize(self, audio_path: Path, num_speakers: int | None = None) -> DiarizationResult: ...

    @abstractmethod
    def is_available(self) -> bool: ...


def get_diarization_adapter() -> DiarizationAdapter:
    from app.config import settings, DiarizationProvider
    if settings.diarization_provider == DiarizationProvider.STUB:
        from app.pipeline.diarization.stub_diarization import StubDiarizationAdapter
        return StubDiarizationAdapter()
    elif settings.diarization_provider == DiarizationProvider.PYANNOTE:
        from app.pipeline.diarization.pyannote_adapter import PyannoteAdapter
        return PyannoteAdapter()
    raise ValueError(f"Unknown diarization provider: {settings.diarization_provider}")
