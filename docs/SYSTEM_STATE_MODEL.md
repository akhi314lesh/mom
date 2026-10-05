# SYSTEM_STATE_MODEL.md

> **Version**: 1.0 (Phase 0)  
> **Last updated**: 2026-10-04

---

## 1. Meeting Lifecycle

```
PREPARING ──► CAPTURING ──► PROCESSING ──► REVIEWING ──► FINALIZED ──► FOLLOW_UP
                                 │
                                 └──► FINALIZED  (if no review items)
```

| State | Description |
|---|---|
| `PREPARING` | Pre-meeting; brief generated; no evidence yet |
| `CAPTURING` | Active recording, overlay, or import in progress |
| `PROCESSING` | Agent pipeline running (ASR → artifacts) |
| `REVIEWING` | Pipeline complete; review queue has pending items |
| `FINALIZED` | Record locked; artifacts generated |
| `FOLLOW_UP` | Action items being tracked in subsequent meetings |

**Transitions:**
- `PREPARING → CAPTURING`: User starts a session or imports a file
- `CAPTURING → PROCESSING`: Session ends or file upload completes
- `PROCESSING → REVIEWING`: Pipeline complete; ≥1 ReviewItem pending
- `PROCESSING → FINALIZED`: Pipeline complete; 0 ReviewItems pending
- `REVIEWING → FINALIZED`: All ReviewItems resolved or dismissed
- `FINALIZED → FOLLOW_UP`: Action items referenced in a later meeting

---

## 2. Processing Status

Independent from lifecycle; tracks the current pipeline run.

```
IDLE ──► QUEUED ──► RUNNING ──► COMPLETE
                        │
                        └──► FAILED (partial outputs preserved)
```

| State | Description |
|---|---|
| `IDLE` | No pipeline running |
| `QUEUED` | Pipeline task enqueued (BackgroundTask) |
| `RUNNING` | One or more stages actively executing |
| `COMPLETE` | All scheduled stages finished successfully |
| `FAILED` | At least one stage failed; partial outputs may exist |

---

## 3. ProcessingRun Status

Per-stage status.

```
QUEUED ──► RUNNING ──► COMPLETE
              │
              ├──► FAILED
              └──► SKIPPED  (input_hash match or not needed)
              └──► INVALIDATED  (dependency correction)
```

---

## 4. Artifact Status

```
CURRENT ◄──── regenerated ──── STALE ──► GENERATING ──► CURRENT
                                                 │
                                                 └──► FAILED
```

---

## 5. Agent OODA Loop

```
OBSERVE
  Read: CaptureSession, EvidenceManifest, existing ProcessingRuns, MeetingRecord

ORIENT
  Determine: what evidence is available, what stages have run, what is uncertain
  Identify: processing gaps, low-confidence fields, ReviewItems needed

ASSESS
  For each pipeline stage:
    - Is output already COMPLETE with current input_hash? → SKIP
    - Is evidence available for this stage? → PROCEED or DEGRADE
    - Is processing necessary given meeting complexity? → TIER SELECTION

PLAN
  Build ordered stage execution plan
  Estimate: cost, latency, tier level
  Select: cheapest path that meets confidence threshold

PRECHECK
  Before executing each stage:
    - Compute input_hash of current evidence
    - Compare with stored ProcessingRun.input_hash
    - If match → skip (idempotency)

EXECUTE
  Run stage via adapter
  Log start/end to ProcessingRun
  Update ProcessingLedger

VERIFY
  Validate outputs:
    - evidence_ids non-empty on all SemanticEvents/Decisions/Actions
    - confidence within expected range
    - no dangling references
  Detect contradictions
  Score confidence fields

REPAIR
  For low-confidence segments (< 0.60):
    - Re-run targeted segment with stronger tier
    - Do NOT reprocess entire meeting

RENDER
  Assemble MeetingRecord from DB
  Build ReviewItem queue (ranked by priority_score)

DELIVER
  Surface MeetingRecord to UI via API
  Generate Artifacts (DOCX, PDF)
  Set Artifact.status = CURRENT

ACCRETE
  Update KnowledgeItems (unverified until confirmed)
  Update TerminologyEntries
  Check cross-meeting ActionItem continuity
  Detect cross-meeting contradictions
```

---

## 6. Capture Session State

```
INITIALIZING ──► ACTIVE ──► PAUSED ──► ACTIVE ──► ENDED
                    │
                    └──► DEGRADED (audio source failure)
                              │
                              └──► ACTIVE (manual-only mode)
```

**Degraded state example:**
```
Microphone fails
  → CaptureSource{source_type=MICROPHONE}.status = FAILED
  → AudioSourceState = NO_AUDIO (or SYSTEM_ONLY if system audio available)
  → EvidenceManifest.unavailable_sources += ["MICROPHONE"]
  → Overlay Shell: remains ACTIVE
  → Manual event capture: remains AVAILABLE
  → WebSocket: sends AudioSourceStateChanged event to frontend
  → UI: shows "MIC UNAVAILABLE — Manual capture active"
```

---

## 7. ReviewItem State

```
PENDING ──► RESOLVED (user confirmed answer)
  │
  ├──► SKIPPED (user dismissed without resolving)
  └──► DEFERRED (user will resolve later)
```

Priority scoring:
```
priority_score = importance × uncertainty × impact

importance: how central to the meeting outcome (0.0–1.0)
uncertainty: 1.0 − confidence
impact:      how much wrong resolution affects the record (0.0–1.0)
```

Items with `priority_score < 0.1` are not surfaced unless the user requests them.

---

## 8. CaptureMode × EvidenceManifest Matrix

| Source | RECORDING | OVERLAY | IMPORT | NOTES_ONLY |
|---|---|---|---|---|
| Audio (mic) | ✓ Optional | ✓ Optional | ✗ | ✗ |
| System audio | ✓ Optional | ✓ Optional (WASAPI) | ✗ | ✗ |
| Timestamps | ✓ | ✓ | ✓ (from file) | ✗ |
| Video | ✓ Optional | ✗ | ✓ Optional | ✗ |
| Manual notes | ✗ | ✓ | ✗ | ✓ |
| User marks | ✗ | ✓ | ✗ | ✗ |
| Imported transcript | ✗ | ✗ | ✓ Optional | ✗ |
| Calendar context | ✓ Future | ✓ Future | ✓ Future | ✓ Future |

If a source is marked ✗ for the current mode, the agent must NOT assume it is available.
