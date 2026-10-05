import { MOCK_DECISIONS, MOCK_MEETINGS, statusBadgeClass, confidenceClass, confidenceLabel } from '../mockData'

export default function Decisions() {
  const confirmed = MOCK_DECISIONS.filter(d => d.status === 'CONFIRMED')
  const candidate = MOCK_DECISIONS.filter(d => d.status === 'CANDIDATE')
  const unresolved = MOCK_DECISIONS.filter(d => d.status === 'UNRESOLVED')

  return (
    <div>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>Decisions</h1>
        <p className="text-muted text-xs mt-2">All decisions across all meetings. Each linked to evidence.</p>
      </div>

      <div className="grid-3 mb-6">
        <div className="metric-card"><div className="metric-label">Confirmed</div><div className="metric-value" style={{ color: 'var(--success)' }}>{confirmed.length}</div></div>
        <div className="metric-card"><div className="metric-label">Candidate</div><div className="metric-value" style={{ color: 'var(--accent)' }}>{candidate.length}</div></div>
        <div className="metric-card"><div className="metric-label">Unresolved</div><div className="metric-value" style={{ color: 'var(--warning)' }}>{unresolved.length}</div></div>
      </div>

      {unresolved.length > 0 && (
        <div style={{ marginBottom: 16, padding: '12px 16px', background: 'var(--warning-dim)', border: '1px solid var(--warning)', borderRadius: 'var(--radius-md)' }}>
          <strong style={{ color: 'var(--warning)', fontSize: 'var(--text-sm)' }}>⚠ {unresolved.length} unresolved decision{unresolved.length !== 1 ? 's' : ''}</strong>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: 4 }}>
            These decisions have contradictions or insufficient consensus evidence. They are preserved as-is until reviewed.
          </div>
        </div>
      )}

      <div className="card">
        {MOCK_DECISIONS.map(d => {
          const meeting = MOCK_MEETINGS.find(m => m.id === d.meeting_id)
          return (
            <div key={d.id} className="decision-card">
              <span style={{ fontSize: 18 }}>✓</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 6 }}>{d.text}</div>
                <div className="flex gap-2 items-center">
                  <span className={`badge ${statusBadgeClass(d.status)}`}>{d.status}</span>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{meeting?.title}</span>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    {d.evidence_ids.length} evidence ref{d.evidence_ids.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
              <div className={`confidence ${confidenceClass(d.confidence)}`}>
                <div className="confidence-dot" />{confidenceLabel(d.confidence)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
