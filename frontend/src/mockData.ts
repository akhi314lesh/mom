// Mock data — Phase 0. Phase 1 replaces with real API calls.

export const MOCK_MEETINGS = [
  {
    id: 'mtg-001',
    title: 'Backend Architecture Planning',
    date: '2026-10-04T10:00:00Z',
    capture_mode: 'IMPORT',
    lifecycle_status: 'REVIEWING',
    processing_status: 'COMPLETE',
    privacy_mode: 'LOCAL',
    quality_metrics: {
      transcript_quality: 0.94,
      speaker_attribution_quality: 0.61,
      decision_certainty: 0.88,
      action_extraction_confidence: 0.91,
      grounding_coverage: 0.97,
      overall_confidence: 0.86,
      weak_areas: ['2 speakers overlap frequently', '1 deadline ambiguous'],
    },
  },
  {
    id: 'mtg-002',
    title: 'Q4 Product Roadmap Review',
    date: '2026-10-02T14:30:00Z',
    capture_mode: 'RECORDING',
    lifecycle_status: 'FINALIZED',
    processing_status: 'COMPLETE',
    privacy_mode: 'LOCAL',
    quality_metrics: {
      transcript_quality: 0.97,
      speaker_attribution_quality: 0.89,
      decision_certainty: 0.93,
      action_extraction_confidence: 0.88,
      grounding_coverage: 0.99,
      overall_confidence: 0.93,
      weak_areas: [],
    },
  },
  {
    id: 'mtg-003',
    title: 'Sprint 12 Retrospective',
    date: '2026-09-28T11:00:00Z',
    capture_mode: 'NOTES_ONLY',
    lifecycle_status: 'FINALIZED',
    processing_status: 'COMPLETE',
    privacy_mode: 'LOCAL',
    quality_metrics: {
      transcript_quality: 0.0,
      speaker_attribution_quality: 0.0,
      decision_certainty: 0.72,
      action_extraction_confidence: 0.78,
      grounding_coverage: 0.80,
      overall_confidence: 0.65,
      weak_areas: ['No audio — notes only mode'],
    },
  },
]

export const MOCK_DECISIONS = [
  { id: 'd-001', meeting_id: 'mtg-001', text: 'Use FastAPI for the backend framework', status: 'CONFIRMED', confidence: 0.92, review_state: 'CONFIRMED', evidence_ids: ['ev-001'] },
  { id: 'd-002', meeting_id: 'mtg-001', text: 'PostgreSQL as the primary database', status: 'CONFIRMED', confidence: 0.88, review_state: 'CONFIRMED', evidence_ids: ['ev-002'] },
  { id: 'd-003', meeting_id: 'mtg-001', text: 'Use Redis for session management', status: 'UNRESOLVED', confidence: 0.45, review_state: 'PENDING', evidence_ids: ['ev-003'] },
  { id: 'd-004', meeting_id: 'mtg-002', text: 'Launch Phase 1 features by end of October', status: 'CONFIRMED', confidence: 0.91, review_state: 'CONFIRMED', evidence_ids: ['ev-010'] },
]

export const MOCK_ACTIONS = [
  { id: 'a-001', task: 'Set up FastAPI project scaffold', owner_name: 'Akhilesh', deadline: '2026-10-11', status: 'PENDING', priority: 'HIGH', confidence: 0.95, owner_confidence: 0.97, deadline_confidence: 0.90, originating_meeting_id: 'mtg-001' },
  { id: 'a-002', task: 'Design the database schema', owner_name: 'Priya', deadline: '2026-10-11', status: 'IN_PROGRESS', priority: 'HIGH', confidence: 0.81, owner_confidence: 0.78, deadline_confidence: 0.82, originating_meeting_id: 'mtg-001' },
  { id: 'a-003', task: 'Research Redis session management options', owner_name: null, deadline: null, status: 'PENDING', priority: 'MEDIUM', confidence: 0.70, owner_confidence: 0.40, deadline_confidence: 0.0, originating_meeting_id: 'mtg-001' },
  { id: 'a-004', task: 'Prepare Phase 1 launch checklist', owner_name: 'Akhilesh', deadline: '2026-10-20', status: 'PENDING', priority: 'CRITICAL', confidence: 0.93, owner_confidence: 0.95, deadline_confidence: 0.88, originating_meeting_id: 'mtg-002' },
]

export const MOCK_REVIEW_ITEMS = [
  { id: 'r-001', type: 'SPEAKER_IDENTITY', question: 'Who is SPEAKER_1? They spoke for 34% of the meeting.', options: ['Akhilesh', 'Priya', 'Someone else'], priority_score: 0.82, context: 'SPEAKER_1 proposed FastAPI and discussed the database schema.', evidence_ids: ['ev-001', 'ev-002'] },
  { id: 'r-002', type: 'AMBIGUOUS_DEADLINE', question: '"End of next week" — does this mean Oct 11 or Oct 14?', options: ['October 11', 'October 14', 'No deadline assigned'], priority_score: 0.65, context: 'Action item: Design the database schema. Owner: Priya.', evidence_ids: ['ev-005'] },
  { id: 'r-003', type: 'UNCERTAIN_OWNER', question: 'Who should own the Redis research task?', options: ['Akhilesh', 'Priya', 'Unassigned'], priority_score: 0.52, context: 'No owner was explicitly mentioned for this task.', evidence_ids: ['ev-003'] },
]

export const MOCK_TRANSCRIPT = [
  { id: 's-001', speaker_id: 'spk-0', speaker_label: 'SPEAKER_0', start_ms: 0, end_ms: 8000, text: "Alright, let's get started. Today we're discussing the backend architecture.", asr_confidence: 0.96 },
  { id: 's-002', speaker_id: 'spk-1', speaker_label: 'SPEAKER_1', start_ms: 8500, end_ms: 28000, text: "I think we should use FastAPI. It's async, well-documented, and the team is familiar with it.", asr_confidence: 0.94 },
  { id: 's-003', speaker_id: 'spk-1', speaker_label: 'SPEAKER_1', start_ms: 18500, end_ms: 28000, text: "And for the database, let's go with PostgreSQL. It fits our relational data model well.", asr_confidence: 0.92 },
  { id: 's-004', speaker_id: 'spk-0', speaker_label: 'SPEAKER_0', start_ms: 28500, end_ms: 40000, text: "So we're going with FastAPI and PostgreSQL then? Everyone on board?", asr_confidence: 0.95 },
  { id: 's-005', speaker_id: 'spk-2', speaker_label: 'SPEAKER_2', start_ms: 40500, end_ms: 48000, text: "Yes, sounds good to me.", asr_confidence: 0.97 },
  { id: 's-006', speaker_id: 'spk-1', speaker_label: 'SPEAKER_1', start_ms: 48500, end_ms: 70000, text: "I'll handle the FastAPI project scaffold. Should be done by next Friday.", asr_confidence: 0.93 },
  { id: 's-007', speaker_id: 'spk-0', speaker_label: 'SPEAKER_0', start_ms: 70500, end_ms: 82000, text: "Priya, can you take a look at the database schema? We need to finalize the entity model.", asr_confidence: 0.91 },
  { id: 's-008', speaker_id: 'spk-2', speaker_label: 'SPEAKER_2', start_ms: 82500, end_ms: 94000, text: "Sure, I can work on that. No specific deadline?", asr_confidence: 0.90 },
  { id: 's-009', speaker_id: 'spk-0', speaker_label: 'SPEAKER_0', start_ms: 94500, end_ms: 105000, text: "Let's say end of next week. Also, should we use Redis for session management? I'm not sure yet.", asr_confidence: 0.88 },
]

export function formatMs(ms: number): string {
  const total = Math.floor(ms / 1000)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export function confidenceClass(c: number): string {
  if (c >= 0.90) return 'conf-high'
  if (c >= 0.60) return 'conf-med'
  return 'conf-low'
}

export function confidenceLabel(c: number): string {
  return `${Math.round(c * 100)}%`
}

export function statusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    CONFIRMED: 'badge-green', CANDIDATE: 'badge-blue', UNRESOLVED: 'badge-yellow',
    FINALIZED: 'badge-green', REVIEWING: 'badge-yellow', PROCESSING: 'badge-yellow',
    CAPTURING: 'badge-blue', PREPARING: 'badge-gray', FOLLOW_UP: 'badge-blue',
    PENDING: 'badge-yellow', IN_PROGRESS: 'badge-blue', COMPLETED: 'badge-green',
    BLOCKED: 'badge-red', CANCELLED: 'badge-gray',
    HIGH: 'badge-red', CRITICAL: 'badge-red', MEDIUM: 'badge-yellow', LOW: 'badge-gray',
  }
  return map[status] ?? 'badge-gray'
}
