# ADR-004: Capture Mode as First-Class Abstraction

**Date**: 2026-10-04  
**Status**: Accepted  
**Deciders**: Lead Architect

---

## Context

The system must support fundamentally different evidence acquisition modes: post-meeting recording import, live overlay capture, file import, and manual notes. These modes have radically different evidence availability profiles.

Early design treated "recording" as the primary mode and others as edge cases. This leads to a pipeline that implicitly assumes audio is always available and fails ungracefully when it isn't.

## Decision

`CaptureMode` is a **first-class system property**, not a feature flag.

Each mode is modeled as an enum value with a declared `EvidenceManifest` that explicitly lists:
- `available_sources: list[str]`
- `unavailable_sources: list[str]`
- `degradation_reason: str | None`

The agent's OODA loop MUST read `CaptureSession.evidence_manifest.unavailable_sources` before every pipeline stage. It MUST NOT execute a stage that requires an unavailable source.

## Rationale

- Prevents the agent from fabricating evidence that doesn't exist
- Enables graceful degradation per mode
- Makes evidence availability explicit and inspectable (visible in Agent Console)
- Allows the system to communicate clearly to the user what it can and cannot process

## Consequences

- Every pipeline stage checks evidence availability before running
- `ProcessingRun.reason` records why a stage was skipped (evidence unavailable)
- The UI always shows the current `CaptureMode` and `AudioSourceState`
- New capture modes can be added by extending the enum + declaring a new EvidenceManifest

## Rejected Alternatives

- **Feature flags per capability**: Creates combinatorial complexity; doesn't compose well
- **Runtime duck-typing** (try and fail): Leads to confusing errors mid-pipeline
