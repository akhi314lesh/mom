# ADR-003: ASR Provider Abstraction

**Date**: 2026-10-04  
**Status**: Accepted

---

## Context

ASR is a foundational pipeline stage but should not be hard-coded to any specific engine.

## Decision

All ASR calls go through an `ASRAdapter` abstract interface:
```python
class ASRAdapter(ABC):
    async def transcribe(self, audio_path: Path, language: str | None) -> ASRResult: ...
```

`ASRResult` contains: `segments: list[ASRSegment]` where each segment has `start_ms`, `end_ms`, `text`, `confidence`, `language`.

Implementations: `WhisperLocalAdapter`, `WhisperAPIAdapter`, `StubASRAdapter`  
Selected via `ASR_PROVIDER` env var.

`StubASRAdapter` returns a pre-defined realistic transcript. This enables complete UI development and pipeline testing without installing torch or any ML packages.

## Consequences

- torch/whisper imports are isolated to `whisper_local.py` and `whisper_api.py`
- The heavy ML stack is optional — `requirements.txt` lists ML packages separately
- `input_hash` in `ProcessingRun` uses hash of the audio file for ASR stage idempotency
