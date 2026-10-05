# ADR-007: Canonical MeetingRecord

**Date**: 2026-10-04  
**Status**: Accepted

---

## Context

Early designs generated free-form prose (summary text) and treated it as the output. This leads to a system where generated text is both the output and, implicitly, the ground truth — making it impossible to verify claims, trace evidence, or regenerate artifacts after corrections.

## Decision

The `MeetingRecord` is the **canonical, authoritative structured representation** of a meeting.

It is an **in-memory aggregate**, assembled from the database at query time. It is NOT stored as a table.

```
MeetingRecord:
  meeting, capture_session, participants, speakers,
  transcript, evidence, events, decisions, action_items,
  questions, contradictions, topics, timeline,
  review_items, quality_metrics, processing_ledger, artifacts
```

All output formats are **renderings** of the MeetingRecord:
- `DocxGenerator.render(record: MeetingRecord) → bytes`
- `PdfGenerator.render(record: MeetingRecord) → bytes`
- Web UI: API returns `MeetingRecord` as JSON; UI renders it

Generated prose (summaries, narration) is NEVER stored as the source of truth. Prose is generated freshly from the MeetingRecord each time an artifact is created.

## Consequences

- When a correction is made, the MeetingRecord is updated, and artifacts are regenerated from it
- DOCX and PDF always reflect the current canonical state
- Evidence links in the MeetingRecord make every claim verifiable
- The UI is always a view of the live MeetingRecord

## Rejected Alternatives

- **Storing generated summary as the source of truth**: Irrecoverable once wrong; cannot be corrected without regenerating
- **Flat document model**: Loses evidence links and provenance
