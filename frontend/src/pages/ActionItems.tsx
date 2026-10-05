import { MOCK_ACTIONS, statusBadgeClass, confidenceClass, confidenceLabel } from '../mockData'

export default function ActionItems() {
  const grouped: Record<string, typeof MOCK_ACTIONS> = {}
  MOCK_ACTIONS.forEach(a => {
    const key = a.originating_meeting_id
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(a)
  })

  const statusCounts = { PENDING: 0, IN_PROGRESS: 0, COMPLETED: 0, BLOCKED: 0 }
  MOCK_ACTIONS.forEach(a => { if (a.status in statusCounts) (statusCounts as any)[a.status]++ })

  return (
    <div>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>Action Items</h1>
        <p className="text-muted text-xs mt-2">Cross-meeting. Action items persist until completed.</p>
      </div>

      <div className="grid-4 mb-6">
        {Object.entries(statusCounts).map(([s, n]) => (
          <div key={s} className="metric-card">
            <div className="metric-label">{s.replace('_', ' ')}</div>
            <div className="metric-value">{n}</div>
          </div>
        ))}
      </div>

      {Object.entries(grouped).map(([meetingId, items]) => (
        <div key={meetingId} className="card mb-4">
          <div className="card-title mb-4" style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
            From: {meetingId}
          </div>
          {items.map(a => (
            <div key={a.id} className="action-card">
              <span style={{ fontSize: 18 }}>⚡</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 6 }}>{a.task}</div>
                <div className="flex gap-2 flex-wrap">
                  <span className={`badge ${statusBadgeClass(a.status)}`}>{a.status}</span>
                  {a.owner_name ? <span className="badge badge-blue">{a.owner_name} <span className={`confidence ${confidenceClass(a.owner_confidence)}`} style={{fontSize:9}}>{confidenceLabel(a.owner_confidence)}</span></span>
                    : <span className="badge badge-red">No owner</span>}
                  {a.deadline ? <span className="badge badge-yellow">Due {a.deadline}</span> : <span className="badge badge-gray">No deadline</span>}
                  <span className={`badge ${statusBadgeClass(a.priority)}`}>{a.priority}</span>
                </div>
              </div>
              <div className={`confidence ${confidenceClass(a.confidence)}`}>
                <div className="confidence-dot" />{confidenceLabel(a.confidence)}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
