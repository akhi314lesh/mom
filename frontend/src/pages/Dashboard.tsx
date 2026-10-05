import { MOCK_MEETINGS, MOCK_ACTIONS, MOCK_DECISIONS, MOCK_REVIEW_ITEMS, statusBadgeClass, confidenceClass, confidenceLabel } from '../mockData'

export default function Dashboard() {
  const pendingActions = MOCK_ACTIONS.filter(a => a.status === 'PENDING' || a.status === 'IN_PROGRESS')
  const pendingReviews = MOCK_REVIEW_ITEMS
  const recentMeetings = MOCK_MEETINGS.slice(0, 3)

  return (
    <div>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, marginBottom: 4 }}>
          Meeting Intelligence
        </h1>
        <p className="text-secondary text-sm">Evidence-grounded — every claim is traceable</p>
      </div>

      {/* Key Metrics */}
      <div className="grid-4 mb-6">
        <div className="metric-card">
          <div className="metric-label">Meetings</div>
          <div className="metric-value">{MOCK_MEETINGS.length}</div>
          <div className="metric-change">↑ 1 this week</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Open Actions</div>
          <div className="metric-value" style={{ color: 'var(--warning)' }}>{pendingActions.length}</div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>across {MOCK_MEETINGS.length} meetings</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Decisions</div>
          <div className="metric-value">{MOCK_DECISIONS.length}</div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
            {MOCK_DECISIONS.filter(d => d.status === 'UNRESOLVED').length} unresolved
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Needs Review</div>
          <div className="metric-value" style={{ color: pendingReviews.length > 0 ? 'var(--error)' : 'var(--success)' }}>
            {pendingReviews.length}
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>review items pending</div>
        </div>
      </div>

      <div className="grid-2 gap-4">
        {/* Recent Meetings */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Recent Meetings</div>
            <a href="/meetings" style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)' }}>View all →</a>
          </div>
          {recentMeetings.map(m => (
            <a href={`/meetings/${m.id}`} key={m.id} style={{ textDecoration: 'none' }}>
              <div style={{ padding: '12px 0', borderBottom: '1px solid var(--border-subtle)', cursor: 'pointer' }}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {m.title}
                    </div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 2 }}>
                      {new Date(m.date).toLocaleDateString()} · {m.capture_mode}
                    </div>
                  </div>
                  <span className={`badge ${statusBadgeClass(m.lifecycle_status)}`}>
                    {m.lifecycle_status}
                  </span>
                </div>
                <div style={{ marginTop: 8 }}>
                  <QualityMini metrics={m.quality_metrics} />
                </div>
              </div>
            </a>
          ))}
        </div>

        {/* Review Queue */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Review Queue</div>
            <span className={`badge ${pendingReviews.length > 0 ? 'badge-red' : 'badge-green'}`}>
              {pendingReviews.length} pending
            </span>
          </div>
          {pendingReviews.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px 0' }}>
              <div className="empty-state-title" style={{ fontSize: 'var(--text-sm)' }}>All caught up!</div>
              <div className="empty-state-desc" style={{ fontSize: 'var(--text-xs)' }}>No items need your attention.</div>
            </div>
          ) : (
            pendingReviews.map(r => (
              <div key={r.id} className={`review-item ${r.priority_score >= 0.7 ? 'high-priority' : 'med-priority'}`} style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 4, fontWeight: 600 }}>
                  {r.type.replace(/_/g, ' ')} · score {r.priority_score.toFixed(2)}
                </div>
                <div className="review-question" style={{ fontSize: 'var(--text-sm)' }}>{r.question}</div>
                <div className="review-options">
                  {r.options.slice(0, 2).map(o => (
                    <div key={o} className="review-option">{o}</div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Open Actions */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Open Actions</div>
            <a href="/actions" style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)' }}>View all →</a>
          </div>
          {pendingActions.map(a => (
            <div key={a.id} className="action-card">
              <span className="decision-icon">⚡</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--text-primary)' }}>{a.task}</div>
                <div className="flex gap-2 mt-2" style={{ flexWrap: 'wrap' }}>
                  {a.owner_name && <span className={`badge badge-blue`}>{a.owner_name}</span>}
                  {a.deadline && <span className="badge badge-yellow">Due {a.deadline}</span>}
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

        {/* Decisions */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Recent Decisions</div>
            <a href="/decisions" style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)' }}>View all →</a>
          </div>
          {MOCK_DECISIONS.map(d => (
            <div key={d.id} className="decision-card">
              <span className="decision-icon">✓</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--text-primary)' }}>{d.text}</div>
                <div className="flex gap-2 mt-2">
                  <span className={`badge ${statusBadgeClass(d.status)}`}>{d.status}</span>
                </div>
              </div>
              <div className={`confidence ${confidenceClass(d.confidence)}`}>
                <div className="confidence-dot" />
                {confidenceLabel(d.confidence)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function QualityMini({ metrics }: { metrics: any }) {
  const bars = [
    { label: 'Transcript', value: metrics.transcript_quality },
    { label: 'Grounding', value: metrics.grounding_coverage },
  ]
  return (
    <div style={{ display: 'flex', gap: 12 }}>
      {bars.map(b => (
        <div key={b.label} style={{ flex: 1 }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>{b.label}</div>
          <div className="quality-track">
            <div className={`quality-fill ${b.value >= 0.9 ? 'high' : b.value >= 0.6 ? 'med' : 'low'}`}
              style={{ width: `${b.value * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}
