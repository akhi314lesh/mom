# ADR-011: Artifact Invalidation and Dependency-Aware Processing

**Date**: 2026-10-04  
**Status**: Accepted

---

## Context

When a user corrects a field (e.g., speaker identity), the naive approach is to rerun the entire pipeline. This is wasteful: ASR doesn't need to rerun because a speaker name was corrected.

The opposite naive approach (no invalidation) produces stale artifacts that don't reflect corrections.

## Decision

### ArtifactStatus

```python
class ArtifactStatus(str, Enum):
    CURRENT    = "CURRENT"
    STALE      = "STALE"
    GENERATING = "GENERATING"
    FAILED     = "FAILED"
```

A correction to the MeetingRecord marks affected `Artifact` records as `STALE`. Stale artifacts are cheaply regenerated from the updated MeetingRecord — NOT by rerunning audio processing.

### Dependency-Aware Invalidation

Each `ProcessingRun` records:
- `input_hash`: SHA-256 of all consumed evidence
- `depends_on_stages`: upstream stages this run depends on

Stage dependency graph:
```
ASR → DIARIZATION → IDENTITY → SEMANTIC → VALIDATION → WORLD_MODEL → ARTIFACTS
```

When a correction occurs at layer X:
1. All `ProcessingRun` records where `stage ∈ descendants(X)` → set `status = INVALIDATED`
2. All `Artifact` records → set `status = STALE`
3. Re-run only invalidated stages
4. Regenerate artifacts from updated MeetingRecord
5. Evidence from non-invalidated stages remains intact

### Idempotency via input_hash

Before re-running any stage:
1. Compute SHA-256 of current input evidence
2. Compare with stored `ProcessingRun.input_hash`
3. If equal → skip (outputs are still valid)
4. If different → run and store new hash

## Consequences

- A speaker correction does NOT rerun ASR ($0 extra cost, no latency)
- All prior Evidence records remain immutable (no data loss)
- `Artifact.stale_reason` provides human-readable explanation
- The UI shows "DOCX is outdated — regenerate?" when status is STALE

## Invariant

**A correction must NOT trigger reprocessing of unrelated pipeline stages.**
