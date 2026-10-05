# ADR-008: Evidence and Provenance Model

**Date**: 2026-10-04  
**Status**: Accepted

---

## Context

For the system to be trustworthy, every extracted claim must be traceable to its source. Users must be able to inspect why the system extracted a decision, who said it, when, and with what confidence.

## Decision

**Evidence records are immutable once stored.**

Every `SemanticEvent`, `Decision`, `ActionItem`, and `Contradiction` must have at least one entry in `evidence_ids`. An empty `evidence_ids` list is a data integrity error that must be raised, not silently accepted.

**Corrections create new Evidence records**, not mutations:
- New `Evidence{source_type=HUMAN_CORRECTION, raw_text="..."}`
- The correcting entity updates its `evidence_ids` to include the new record
- The original Evidence record remains unchanged with its original provenance

**Evidence fields:**
- `source_type`: TRANSCRIPT | USER_MARK | MANUAL | IMPORT_DOC | HUMAN_CORRECTION
- `timestamp_ms`: meeting-relative milliseconds
- `confidence`: field-level float
- `processing_run_id`: which pipeline run produced this evidence

## Consequences

- Full audit trail: every state change is traceable
- Old Evidence is never lost — contradictions can be reconstructed
- Human corrections are first-class evidence (not just DB updates)
- The UI can show the full evidence chain for any claim
