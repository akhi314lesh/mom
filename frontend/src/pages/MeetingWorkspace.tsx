import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { MOCK_MEETINGS, MOCK_DECISIONS, MOCK_ACTIONS, MOCK_TRANSCRIPT, MOCK_REVIEW_ITEMS, formatMs, confidenceClass, confidenceLabel, statusBadgeClass } from '../mockData'

type Tab = 'transcript' | 'decisions' | 'actions' | 'review' | 'timeline'

export default function MeetingWorkspace() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState<Tab>('decisions')
  const [evidenceTarget, setEvidenceTarget] = useState<string | null>(null)

  const meeting = MOCK_MEETINGS.find(m => m.id === id) ?? MOCK_MEETINGS[0]
  const decisions = MOCK_DECISIONS.filter(d => d.meeting_id === meeting.id)
  const actions = MOCK_ACTIONS.filter(a => a.originating_meeting_id === meeting.id)
  const reviews = MOCK_REVIEW_ITEMS

  return (
    <div style={{ display: 'flex', gap: 20, height: '100%', overflow: 'hidden' }}>
      {/* Main panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        {/* Meeting header */}
        <div className="card mb-4" style={{ flexShrink: 0 }}>
          <div className="flex items-center gap-4">
            <div style={{ flex: 1 }}>
              <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginBottom: 4 }}>{meeting.title}</h1>
              <div className="flex gap-2 items-center">
                <span className={`badge ${statusBadgeClass(meeting.lifecycle_status)}`}>{meeting.lifecycle_status}</span>
                <span className={`badge ${meeting.capture_mode === 'IMPORT' ? 'badge-blue' : 'badge-green'}`}>{meeting.capture_mode}</span>
                <span className="text-muted text-xs">{new Date(meeting.date).toLocaleDateString()}</span>
                <span className="text-muted text-xs">·</span>
                <span className="text-muted text-xs">{meeting.privacy_mode}</span>
              </div>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-secondary btn-sm">Download DOCX</button>
              <button className="btn btn-secondary btn-sm">Download PDF</button>
            </div>
          </div>

          {/* Quality metrics bar */}
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
              Quality Metrics
            </div>
            {[
              { label: 'Transcript Quality', key: 'transcript_quality' },
              { label: 'Speaker Attribution', key: 'speaker_attribution_quality' },
              { label: 'Decision Certainty', key: 'decision_certainty' },
              { label: 'Evidence Grounding', key: 'grounding_coverage' },
            ].map(({ label, key }) => {
              const val = (meeting.quality_metrics as any)[key] as number
              return (
                <div key={key} className="quality-bar">
                  <div className="quality-label">{label}</div>
                  <div className="quality-track">
                    <div className={`quality-fill ${val >= 0.9 ? 'high' : val >= 0.6 ? 'med' : 'low'}`}
                      style={{ width: `${val * 100}%` }} />
                  </div>
                  <div className="quality-pct">{val > 0 ? confidenceLabel(val) : '—'}</div>
                </div>
              )
            })}
            {meeting.quality_metrics.weak_areas.length > 0 && (
              <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                {meeting.quality_metrics.weak_areas.map(w => (
                  <span key={w} className="badge badge-yellow" style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
                    ⚠ {w}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Tab nav */}
        <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 16, flexShrink: 0 }}>
          {([
            ['decisions', `✓ Decisions (${decisions.length})`],
            ['actions', `⚡ Actions (${actions.length})`],
            ['review', `◆ Review (${reviews.length})`],
            ['transcript', '▤ Transcript'],
            ['timeline', '◎ Timeline'],
          ] as [Tab, string][]).map(([t, label]) => (
            <button key={t} onClick={() => setTab(t)}
              style={{
                padding: '10px 16px', fontSize: 'var(--text-sm)', fontWeight: tab === t ? 600 : 400,
                color: tab === t ? 'var(--accent)' : 'var(--text-muted)',
                background: 'none', borderBottom: tab === t ? '2px solid var(--accent)' : '2px solid transparent',
                marginBottom: -1, transition: 'all 150ms',
              }}>
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {tab === 'decisions' && (
            <div>
              {decisions.map(d => (
                <div key={d.id} className="decision-card" style={{ cursor: 'pointer' }} onClick={() => setEvidenceTarget(d.id)}>
                  <span className="decision-icon" style={{ fontSize: 18 }}>✓</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>{d.text}</div>
                    <div className="flex gap-2 items-center">
                      <span className={`badge ${statusBadgeClass(d.status)}`}>{d.status}</span>
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                        {d.evidence_ids.length} evidence ref{d.evidence_ids.length !== 1 ? 's' : ''}
                      </span>
                      <button onClick={e => { e.stopPropagation(); setEvidenceTarget(d.id) }}
                        style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)', background: 'none', padding: 0 }}>
                        View source →
                      </button>
                    </div>
                  </div>
                  <div className={`confidence ${confidenceClass(d.confidence)}`}>
                    <div className="confidence-dot" />
                    {confidenceLabel(d.confidence)}
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'actions' && (
            <div>
              {actions.map(a => (
                <div key={a.id} className="action-card">
                  <span className="decision-icon" style={{ fontSize: 18 }}>⚡</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>{a.task}</div>
                    <div className="flex gap-2 items-center flex-wrap">
                      <span className={`badge ${statusBadgeClass(a.status)}`}>{a.status}</span>
                      {a.owner_name ? (
                        <span className="flex items-center gap-1">
                          <span className="badge badge-blue">{a.owner_name}</span>
                          <span className={`confidence ${confidenceClass(a.owner_confidence)}`} style={{ fontSize: 10 }}>
                            <div className="confidence-dot" />{confidenceLabel(a.owner_confidence)}
                          </span>
                        </span>
                      ) : (
                        <span className="badge badge-red">No owner</span>
                      )}
                      {a.deadline ? (
                        <span className="flex items-center gap-1">
                          <span className="badge badge-yellow">Due {a.deadline}</span>
                          <span className={`confidence ${confidenceClass(a.deadline_confidence)}`} style={{ fontSize: 10 }}>
                            <div className="confidence-dot" />{confidenceLabel(a.deadline_confidence)}
                          </span>
                        </span>
                      ) : (
                        <span className="badge badge-gray">No deadline</span>
                      )}
                      <span className={`badge ${statusBadgeClass(a.priority)}`}>{a.priority}</span>
                    </div>
                  </div>
                  <div className={`confidence ${confidenceClass(a.confidence)}`}>
                    <div className="confidence-dot" />
                    {confidenceLabel(a.confidence)}
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'review' && (
            <div>
              {reviews.map(r => (
                <div key={r.id} className={`review-item ${r.priority_score >= 0.7 ? 'high-priority' : 'med-priority'}`}>
                  <div className="flex items-center gap-2 mb-3">
                    <span className={`badge ${r.priority_score >= 0.7 ? 'badge-red' : 'badge-yellow'}`}>
                      {r.type.replace(/_/g, ' ')}
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      priority {r.priority_score.toFixed(2)}
                    </span>
                  </div>
                  <div className="review-question">{r.question}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 10, fontStyle: 'italic' }}>{r.context}</div>
                  <div className="review-options">
                    {r.options.map(o => <div key={o} className="review-option">{o}</div>)}
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button className="btn btn-primary btn-sm">Confirm</button>
                    <button className="btn btn-ghost btn-sm">Skip</button>
                    <button className="btn btn-ghost btn-sm">Defer</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'transcript' && (
            <div>
              {MOCK_TRANSCRIPT.map(s => (
                <div key={s.id} className="transcript-segment">
                  <span className="transcript-timestamp">{formatMs(s.start_ms)}</span>
                  <span className="transcript-speaker">{s.speaker_label}</span>
                  <div style={{ flex: 1 }}>
                    <div className="transcript-text">{s.text}</div>
                    <div className={`confidence ${confidenceClass(s.asr_confidence)}`} style={{ marginTop: 4, fontSize: 10 }}>
                      <div className="confidence-dot" />
                      ASR {confidenceLabel(s.asr_confidence)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'timeline' && (
            <div>
              <div className="timeline">
                {MOCK_DECISIONS.map(d => (
                  <div key={d.id} className="timeline-item decision">
                    <div className="timeline-time">{formatMs(2000)}</div>
                    <div className="timeline-text"><strong>Decision:</strong> {d.text}</div>
                  </div>
                ))}
                {MOCK_ACTIONS.map(a => (
                  <div key={a.id} className="timeline-item action">
                    <div className="timeline-time">{formatMs(50000)}</div>
                    <div className="timeline-text"><strong>Action:</strong> {a.task}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Evidence Panel */}
      {evidenceTarget && (
        <div style={{ width: 300, flexShrink: 0 }}>
          <div className="card" style={{ height: '100%', overflow: 'auto' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="card-title">Evidence</div>
              <button onClick={() => setEvidenceTarget(null)} className="btn btn-ghost btn-sm">✕</button>
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 12 }}>
              Source evidence for this claim.
            </div>
            <div className="evidence-card">
              <div className="flex gap-2 mb-2">
                <span className="badge badge-green">TRANSCRIPT</span>
                <span className="badge badge-gray">AUDIO</span>
              </div>
              <div className="evidence-quote">
                "Let's use FastAPI — it's async, well-documented, and the team is familiar with it."
              </div>
              <div className="flex gap-2 mt-2">
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>SPEAKER_1</span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>·</span>
                <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>00:08</span>
                <span className="ml-auto">
                  <div className={`confidence ${confidenceClass(0.94)}`} style={{ fontSize: 10 }}>
                    <div className="confidence-dot" />0.94
                  </div>
                </span>
              </div>
              <button className="btn btn-ghost btn-sm mt-2 w-full" onClick={() => setTab('transcript')}>
                Jump to source →
              </button>
            </div>
            <div style={{ marginTop: 12, padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              <strong style={{ color: 'var(--text-secondary)' }}>Processing stage:</strong> SEMANTIC<br />
              <strong style={{ color: 'var(--text-secondary)' }}>Extraction model:</strong> stub (Phase 0)
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
