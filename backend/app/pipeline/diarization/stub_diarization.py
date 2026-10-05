"""pipeline/diarization/stub_diarization.py — Stub diarization adapter."""
from pathlib import Path
from app.pipeline.diarization.diarization_adapter import DiarizationAdapter, DiarizationResult, DiarizationSegment

_MOCK_SEGMENTS = [
    DiarizationSegment(speaker_label="SPEAKER_0", start_ms=0,     end_ms=8000,   confidence=0.95),
    DiarizationSegment(speaker_label="SPEAKER_1", start_ms=8500,  end_ms=28000,  confidence=0.93),
    DiarizationSegment(speaker_label="SPEAKER_0", start_ms=28500, end_ms=40000,  confidence=0.94),
    DiarizationSegment(speaker_label="SPEAKER_2", start_ms=40500, end_ms=48000,  confidence=0.97),
    DiarizationSegment(speaker_label="SPEAKER_1", start_ms=48500, end_ms=70000,  confidence=0.92),
    DiarizationSegment(speaker_label="SPEAKER_0", start_ms=70500, end_ms=82000,  confidence=0.91),
    DiarizationSegment(speaker_label="SPEAKER_2", start_ms=82500, end_ms=94000,  confidence=0.89),
    DiarizationSegment(speaker_label="SPEAKER_1", start_ms=94500, end_ms=105000, confidence=0.90),
]


class StubDiarizationAdapter(DiarizationAdapter):
    async def diarize(self, audio_path: Path, num_speakers: int | None = None) -> DiarizationResult:
        return DiarizationResult(segments=_MOCK_SEGMENTS, num_speakers=3, adapter_used="StubDiarizationAdapter")

    def is_available(self) -> bool:
        return True
