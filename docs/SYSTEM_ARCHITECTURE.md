# SYSTEM_ARCHITECTURE.md

> **Version**: 1.0 (Phase 0)  
> **Last updated**: 2026-10-04

---

## 1. System Philosophy

This system is an **evidence-grounded meeting intelligence operating system**.

Every important extracted claim is traceable to:
- A transcript span (start_ms – end_ms)
- A speaker (label + resolved participant)
- A timestamp (meeting-relative ms)
- A source modality (AUDIO | MANUAL | IMPORT_DOC | USER_MARK)
- A confidence score (field-level float)
- A processing stage (which ProcessingRun produced it)

**Generated prose is never the source of truth. Evidence is.**

---

## 2. 12-Layer System Model

```
┌──────────────────────────────────────────────────────────────────────┐
│ LAYER 0 — RAW INPUTS                                                 │
│  Audio · Video · Manual Input · Imported Files · Meeting Context     │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 1 — EVIDENCE                                                   │
│  Timestamped, immutable, source-tagged Evidence records              │
│  Evidence is the authoritative ground truth                          │
│  Evidence is never mutated. Corrections create new Evidence records. │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 2 — PERCEPTION                                                 │
│  ASR · Diarization · Segmentation · Normalization                    │
│  Output: TranscriptSegment[] with asr_confidence per segment         │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 3 — IDENTITY                                                   │
│  Speaker ↔ Participant resolution · Entity resolution                │
│  Output: Speaker[] with resolved Participant links + confidence       │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 4 — SEMANTIC EVENTS                                            │
│  Ideas · Suggestions · Opinions · Decisions · Commitments           │
│  Actions · Questions · Blockers · Contradictions · User Marks        │
│  Output: SemanticEvent[] (each grounded in Evidence)                 │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 5 — MEETING WORLD MODEL                                        │
│  Structured, evolving understanding of the meeting                   │
│  Decisions · Actions · Questions · Blockers · Timeline               │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 6 — VALIDATION                                                 │
│  Grounding · Confidence scoring · Contradiction checking             │
│  Consistency validation · Evidence coverage                          │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 7 — CANONICAL MEETING RECORD                                   │
│  Authoritative structured meeting state (in-memory aggregate)        │
│  DOCX/PDF/UI are RENDERINGS of this record, not the truth itself    │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 8 — HUMAN REVIEW                                               │
│  Focused, ranked, minimal-interruption correction queue              │
│  Human-confirmed changes propagate back to layers 1–7               │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 9 — PRESENTATION                                               │
│  Web UI · Desktop Overlay · Timeline · Evidence Explorer             │
│  Agent Console · Meeting Workspace                                   │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 10 — ARTIFACTS                                                 │
│  DOCX · PDF · JSON · CSV · Transcript.txt · Evidence.json           │
│  All generated from MeetingRecord. Status: CURRENT|STALE|GENERATING  │
├──────────────────────────────────────────────────────────────────────┤
│ LAYER 11 — KNOWLEDGE ACCRETION                                       │
│  Cross-meeting memory · Terminology · Learned corrections            │
│  Persistent organizational intelligence                              │
└──────────────────────────────────────────────────────────────────────┘

                    ↕ AGENT CONTROL PLANE ↕
   OBSERVE→ORIENT→ASSESS→PLAN→PRECHECK→EXECUTE→VERIFY→REPAIR→
   RENDER→DELIVER→ACCRETE
```

---

## 3. Capture Mode Abstraction

Capture Mode is a **system property**, not a feature. It governs what evidence is available to the entire pipeline.

```
CaptureMode:
  RECORDING    Post-meeting audio/video file
  OVERLAY      Live always-on-top capture surface
  IMPORT       External audio/video/transcript/document
  NOTES_ONLY   Manual structured input only
```

Each mode declares:
- Available evidence sources
- Unavailable evidence sources
- Capture capabilities
- Processing capabilities
- Failure modes
- Privacy implications

The agent MUST read `CaptureSession.evidence_manifest.unavailable_sources` before any pipeline stage. Never fabricate evidence for an unavailable source.

### Audio Source State

```
AudioSourceState:
  MICROPHONE_ONLY
  SYSTEM_ONLY
  MICROPHONE_AND_SYS
  NO_AUDIO
```

The UI must reflect the current `AudioSourceState` with unambiguous indicators. It must never display "Recording" when `state == NO_AUDIO`.

---

## 4. Desktop Overlay Architecture

The Overlay Shell and Capture Controllers are **independent subsystems**. A Capture Controller failure must NOT kill the Overlay Shell.

```
┌─────────────────────────────────────────────┐
│            OVERLAY SHELL                    │
│  (always-on-top window, always operational) │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │       CAPTURE CONTROLLERS           │   │
│  │  ┌──────────┐  ┌──────────────────┐ │   │
│  │  │ MicCtrl  │  │ SystemAudioCtrl  │ │   │
│  │  │ ACTIVE / │  │ UNAVAILABLE      │ │   │
│  │  │ FAILED   │  │ (Windows limit)  │ │   │
│  │  └──────────┘  └──────────────────┘ │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │     MANUAL EVENT CONTROLLERS        │   │
│  │  [+ Note] [✓ Decision] [⚡ Action]   │   │
│  │  [? Flag] [⏱ Mark Moment]           │   │
│  │  Always operational                  │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  WebSocket → Backend (Meeting session)      │
└─────────────────────────────────────────────┘
```

**Windows audio capture strategy:**
- Microphone: `sounddevice` (PyAudio fallback)
- System audio loopback: WASAPI loopback via `sounddevice` with `hostapi='wasapi'`
- If WASAPI unavailable: fall back to mic-only; log `AUDIO_SOURCE_DEGRADED`

---

## 5. Processing Pipeline

```
File Upload / Live Audio
        ↓
[ASR Adapter] ─────────────────────────── produces TranscriptSegment[]
        ↓
[Diarization Adapter] ─────────────────── assigns speaker labels
        ↓
[Normalizer] ──────────────────────────── cleans, timestamps, merges
        ↓
[Identity Resolver] ────────────────────── Speaker ↔ Participant
        ↓
[Semantic Engine] ──────────────────────── SemanticEvent[] extraction
  ├── DecisionExtractor
  ├── ActionExtractor
  ├── QuestionExtractor
  └── ContradictionDetector
        ↓
[Grounding Validator] ──────────────────── evidence link verification
        ↓
[Confidence Scorer] ────────────────────── field-level confidence
        ↓
[World Model Builder] ──────────────────── MeetingRecord assembly
        ↓
[Artifact Generator] ───────────────────── DOCX / PDF
```

Each stage is a `PipelineStage` with:
- `input_hash` for idempotency
- `depends_on_stages` for dependency-aware invalidation
- Logged to `ProcessingRun` and `ProcessingLedger`

---

## 6. Provider Abstractions

All ML/AI dependencies are behind abstract adapter interfaces.

| Abstraction | Interface | Implementations |
|---|---|---|
| ASR | `ASRAdapter` | `WhisperLocalAdapter`, `WhisperAPIAdapter`, `StubASRAdapter` |
| Diarization | `DiarizationAdapter` | `PyannoteAdapter`, `StubDiarizationAdapter` |
| LLM | `LLMAdapter` | `OpenAIAdapter`, `AnthropicAdapter`, `OllamaAdapter`, `StubLLMAdapter` |

Selected via environment variables: `ASR_PROVIDER`, `DIARIZATION_PROVIDER`, `LLM_PROVIDER`.

The `Stub*` adapters return realistic deterministic mock data and enable full UI/pipeline development without any API keys or ML packages.

---

## 7. Dependency-Aware Invalidation

```
Stage dependency graph:
  ASR → DIARIZATION → IDENTITY → SEMANTIC → VALIDATION → WORLD_MODEL → ARTIFACTS

Correction: Human fixes speaker identity (IDENTITY layer)
  → ASR:         remains COMPLETE
  → DIARIZATION: remains COMPLETE
  → IDENTITY:    INVALIDATED
  → SEMANTIC:    INVALIDATED (depends on IDENTITY)
  → VALIDATION:  INVALIDATED
  → WORLD_MODEL: INVALIDATED
  → ARTIFACTS:   status → STALE (regenerate cheaply)

ASR is never rerun unless audio input literally changes.
Evidence records from all prior runs remain intact and immutable.
```

---

## 8. Artifact Status

```
ArtifactStatus:
  CURRENT    Artifact reflects current MeetingRecord
  STALE      MeetingRecord changed; regeneration needed
  GENERATING Regeneration in progress
  FAILED     Last generation attempt failed
```

A STALE artifact triggers cheap regeneration from the current MeetingRecord, not a full pipeline rerun.

---

## 9. Semantic Event Taxonomy

```
IDEA · SUGGESTION · OPINION · DISCUSSION
DECISION_CANDIDATE · DECISION_CONFIRMED
COMMITMENT · ACTION_ITEM
QUESTION · ANSWER
BLOCKER · RISK · DEADLINE · STATUS_UPDATE
DISAGREEMENT · CONTRADICTION
USER_MARK
```

**Escalation invariant:** SUGGESTION → DECISION requires consensus evidence. OPINION → DECISION is never automatic. The system must prefer DECISION UNRESOLVED over inventing a resolution.

---

## 10. Architectural Invariants

These rules must not be violated by any implementation:

1. Evidence is the ground truth. Generated prose is never authoritative.
2. MeetingRecord is the canonical aggregate. DOCX/PDF/UI are renderings.
3. Every extracted claim must have at least one `evidence_ids` entry.
4. The Overlay Shell is independent of Capture Controllers.
5. Capture mode governs evidence availability. Agent must read EvidenceManifest.
6. Confidence is field-level, not meeting-level.
7. Human attention is a limited resource. Review items are ranked and minimized.
8. Evidence records are immutable. Corrections create new Evidence records.
9. Pipeline stages are idempotent (input_hash). Re-run only if inputs changed.
10. SUGGESTION/OPINION → DECISION requires consensus evidence.
11. Contradictions must be surfaced, never silently resolved.
12. ActionItems are cross-meeting entities. They survive beyond their originating meeting.
13. Processing cost and latency are tracked in ProcessingLedger.
14. Privacy mode is explicit. UI shows what is processed locally vs. remotely.
15. Pipeline stage failure must not destroy prior stage outputs.
16. Inferred knowledge is never silently promoted to verified knowledge.
17. No claim without evidence. Empty evidence_ids is a data integrity error.
18. A correction must NOT trigger reprocessing of unrelated pipeline stages.
