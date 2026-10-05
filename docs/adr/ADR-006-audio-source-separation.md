# ADR-006: Audio Source Separation

**Date**: 2026-10-04  
**Status**: Accepted

---

## Context

"Recording" can mean microphone capture, system audio loopback, both mixed, or neither. These are different evidence sources with different capture mechanisms and different failure modes.

Early designs conflated "recording" with "microphone" which would fail silently when system audio was needed or when the mic was unavailable.

## Decision

Audio sources are explicitly modeled as `AudioSourceState`:

```python
class AudioSourceState(str, Enum):
    MICROPHONE_ONLY    = "MICROPHONE_ONLY"
    SYSTEM_ONLY        = "SYSTEM_ONLY"
    MICROPHONE_AND_SYS = "MICROPHONE_AND_SYS"
    NO_AUDIO           = "NO_AUDIO"
```

Each source is a separate `CaptureSource` entity with its own `status` field.

**Windows-specific implementation:**
- Microphone: `sounddevice` default device
- System audio loopback: `sounddevice` with `hostapi='wasapi'`, `exclusive=False`
- If WASAPI unavailable: fall back to MICROPHONE_ONLY + log `AUDIO_SOURCE_DEGRADED`

The UI must never show "Recording" when `AudioSourceState == NO_AUDIO`.

## Consequences

- `CaptureSession.audio_source_state` is updated in real time
- The Overlay Shell displays the current source state with unambiguous indicators
- WebSocket broadcasts `AudioSourceStateChanged` events to both the overlay and the main UI
- The agent reads `AudioSourceState` before scheduling ASR to determine which audio streams are available
