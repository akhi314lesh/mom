# AGENTS.md — AI Meeting Intelligence System

> **For any AI agent entering this repository.**
> Read this file first. It is not optional.

---

## What This System Is

This is an **evidence-grounded meeting intelligence operating system**.

It is NOT:
- An AI transcription + summarization app
- A chatbot wrapper around Whisper + GPT
- A CRUD app with some AI features

It IS:
- A structured system that ingests meeting evidence (audio, notes, marks)
- Extracts structured meaning (decisions, actions, questions, contradictions)
- Maintains a canonical MeetingRecord grounded in evidence
- Supports human correction with minimal interruption
- Generates verifiable, evidence-backed artifacts (DOCX, PDF)
- Accretes organizational knowledge across meetings

---

## Current State

See [CAPABILITIES.md](CAPABILITIES.md) for what is currently implemented.

The `CAPABILITIES.md` file is updated at the end of each phase. If you are unsure what works, read that file before assuming anything.

---

## Repository Structure

See [REPOSITORY_MAP.md](REPOSITORY_MAP.md) for the full file-by-file map.

```
mom/
├── backend/        Python FastAPI backend
├── frontend/       React + TypeScript frontend (Vite)
├── docs/           Architecture documentation + ADRs
├── README.md
└── .gitignore
```

---

## Architecture Overview

See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) for the full architecture.

The system operates in 12 layers:

```
Layer 0:  Raw Inputs (audio, video, notes, marks)
Layer 1:  Evidence (immutable, timestamped, source-tagged)
Layer 2:  Perception (ASR, diarization, segmentation)
Layer 3:  Identity (speaker ↔ participant resolution)
Layer 4:  Semantic Events (decisions, actions, contradictions...)
Layer 5:  Meeting World Model (structured understanding)
Layer 6:  Validation (grounding, confidence, consistency)
Layer 7:  Canonical Meeting Record (authoritative state)
Layer 8:  Human Review (ranked, minimal interruption)
Layer 9:  Presentation (web UI, overlay, timeline)
Layer 10: Artifacts (DOCX, PDF, JSON, CSV)
Layer 11: Knowledge Accretion (cross-meeting memory)
```

---

## Domain Model

See [DATA_AND_PROVENANCE_MODEL.md](DATA_AND_PROVENANCE_MODEL.md) for all 22 entities.

The central abstraction is the **MeetingRecord** — an in-memory aggregate assembled from the DB. DOCX, PDF, and the UI are renderings of the MeetingRecord, not of free-form prose.

---

## How the Agent Operates

The agent (orchestrated processing pipeline) follows the OODA loop:

```
OBSERVE   → read CaptureSession, available evidence, existing ProcessingRuns
ORIENT    → identify what is known, what is missing, what is uncertain
ASSESS    → determine whether each pipeline stage is necessary
PLAN      → build processing plan with cost/latency estimates
PRECHECK  → check if stage output already exists (idempotency via input_hash)
EXECUTE   → run only necessary stages; log every run to ProcessingLedger
VERIFY    → validate outputs; check confidence; detect contradictions
REPAIR    → targeted repair of low-confidence segments
RENDER    → assemble MeetingRecord from all stage outputs
DELIVER   → surface to UI + generate artifacts
ACCRETE   → update KnowledgeItems, Terminology, cross-meeting state
```

The agent must **never run expensive stages unnecessarily**. See [RESOURCE_AWARE_EXECUTION.md](RESOURCE_AWARE_EXECUTION.md).

---

## Critical Rules for Agents Working in This Codebase

### Evidence
- Every `SemanticEvent`, `Decision`, `ActionItem`, `Contradiction` MUST have at least one `evidence_ids` entry
- An empty `evidence_ids` list is a data integrity error — raise it, don't silently accept it
- `Evidence` records are immutable. Corrections create NEW Evidence records

### Processing
- Before running any stage, check `ProcessingRun.input_hash` — if inputs unchanged, SKIP
- A speaker correction invalidates IDENTITY + downstream only. It does NOT invalidate ASR
- See [DATA_AND_PROVENANCE_MODEL.md](DATA_AND_PROVENANCE_MODEL.md) for the stage dependency graph

### Artifacts
- When a MeetingRecord changes, set affected `Artifact.status = STALE`
- Never auto-rerun ASR because an artifact was stale
- Regenerate DOCX/PDF cheaply from the updated MeetingRecord

### Confidence
- Confidence is field-level, not meeting-level
- Items with confidence < 0.60 go to the review queue at HIGH priority
- NEVER present a low-confidence fact as a verified fact

### Knowledge Accretion
- `KnowledgeItem.verified = True` requires human confirmation OR system confidence ≥ threshold
- `verification_source = INFERRED` is never sufficient to set `verified = True`
- New terminology corrections apply to future meetings — not retroactively without human confirmation

### Capture Mode
- Always read `CaptureSession.evidence_manifest.unavailable_sources` before any pipeline stage
- Never fabricate evidence for an unavailable source
- If a stage requires an unavailable source, log the gap in ProcessingRun and degrade gracefully

### Overlay
- The Overlay Shell must remain operational even if microphone, system audio, or STT fails
- Overlay Shell and Capture Controllers are separate systems
- A mic failure → update `AudioSourceState`, keep overlay functional, keep manual marks available

---

## Questions an Agent Should Be Able to Answer

After reading the documentation, an agent should be able to answer:

1. **What is this system?** → Evidence-grounded meeting intelligence OS
2. **What state is it in?** → See CAPABILITIES.md
3. **What evidence exists?** → CaptureSession.evidence_manifest + Evidence table
4. **What does the system currently believe?** → MeetingRecord aggregate
5. **Why does it believe that?** → Evidence.id refs on every SemanticEvent/Decision/Action
6. **What is uncertain?** → ReviewItem table, low-confidence fields
7. **What should I do next?** → See ROADMAP.md current phase
8. **What is the cheapest action to resolve uncertainty?** → See RESOURCE_AWARE_EXECUTION.md
9. **What can I safely change?** → Anything that creates new Evidence; never mutate existing Evidence
10. **How do I verify the change?** → Run the system, check output, inspect evidence links
11. **What knowledge should I preserve?** → Create/update relevant ADR if deviating from architecture

---

## Adding a New Feature

1. Check if it fits an existing domain entity or requires a new one
2. If new entity: update DATA_AND_PROVENANCE_MODEL.md + add Alembic migration
3. If new pipeline stage: register in the dependency graph (depends_on_stages)
4. If architectural deviation: create an ADR in `docs/adr/`
5. Ensure evidence is captured and confidence is assigned
6. Update CAPABILITIES.md after implementation
7. Commit with phase-tagged message: `feat(phase-N): description`

---

## Do Not

- Do not add LLM calls without a provider abstraction layer
- Do not hardcode Whisper or any specific model name as an architecture foundation
- Do not store generated prose as the source of truth
- Do not create features that work only when all pipeline stages succeed
- Do not expose LLM chain-of-thought to the user — expose evidence and rationale only
- Do not run the full pipeline when only artifact regeneration is needed
- Do not move `SUGGESTION` → `DECISION` without consensus evidence
- Do not silently resolve contradictions
