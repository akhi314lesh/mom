# ADR-005: Overlay Architecture

**Date**: 2026-10-04  
**Status**: Accepted  
**Deciders**: Lead Architect

---

## Context

The system requires a desktop overlay that is always-on-top, low-distraction, and operational during live meetings. The overlay must work even when audio capture or transcription fails.

## Decision

The **Overlay Shell** and **Capture Controllers** are architecturally independent subsystems.

```
Overlay Shell (always-on-top window)
  └── Capture Controllers (can fail independently)
        ├── MicrophoneController
        ├── SystemAudioController
        └── ManualEventController (always available)
```

A failure of any Capture Controller must NOT affect the Overlay Shell's availability. The shell always renders. Manual event capture always works.

**Implementation**: `pywebview` opens a frameless always-on-top browser window at `http://localhost:8001/overlay`. Communication with the main backend via WebSocket.

**Fallback**: If pywebview unavailable, open system browser at overlay URL (loses always-on-top, but manual marks still work).

## Rationale

- Critical UX requirement: user must be able to mark moments even if recording fails
- pywebview is lightweight (no Electron), cross-platform, and ships no separate browser
- WebSocket provides real-time sync with backend without polling

## Consequences

- Overlay launches as a separate process managed by `overlay_manager.py`
- `AudioSourceState` is broadcast via WebSocket to the overlay in real time
- Global hotkey (Ctrl+Shift+M) is registered by `hotkey_manager.py` independently

## Rejected Alternatives

- **Electron**: ~150MB overhead; overkill for a small overlay window
- **Tkinter**: Limited CSS styling; harder to match web UI design language
- **System tray only**: Too limited for the required capture controls
