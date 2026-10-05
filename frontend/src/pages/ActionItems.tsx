import { useState, useEffect } from 'react'

interface ActionItem {
  id: string
  task: string
  status: string
  priority: string
  deadline: string | null
  confidence: number
  owner_id: string | null
  owner_name: string | null
  originating_meeting_id: string
  originating_meeting_title: string
  originating_meeting_date: string | null
  last_updated_meeting_id: string | null
  last_updated_meeting_title: string | null
  evidence_count: number
}

function statusBadgeClass(status: string) {
  switch (status) {
    case 'COMPLETED':
      return 'badge-green'
    case 'IN_PROGRESS':
      return 'badge-blue'
    case 'BLOCKED':
      return 'badge-red'
    case 'CANCELLED':
      return 'badge-gray'
    default:
      return 'badge-yellow'
  }
}

export default function ActionItems() {
  const [actions, setActions] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(false)
  const [filterStatus, setFilterStatus] = useState('ALL')

  const fetchActions = async () => {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/continuity/actions')
      if (res.ok) {
        const data = await res.json()
        setActions(data || [])
      }
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    fetchActions()
  }, [])

  const handleStatusChange = async (actionId: string, newStatus: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/continuity/actions/${actionId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      if (res.ok) {
        setActions((prev) =>
          prev.map((a) => (a.id === actionId ? { ...a, status: newStatus } : a))
        )
      }
    } catch {}
  }

  const statusCounts = {
    PENDING: actions.filter((a) => a.status === 'PENDING').length,
    IN_PROGRESS: actions.filter((a) => a.status === 'IN_PROGRESS').length,
    COMPLETED: actions.filter((a) => a.status === 'COMPLETED').length,
    BLOCKED: actions.filter((a) => a.status === 'BLOCKED').length,
  }

  const filtered = actions.filter(
    (a) => filterStatus === 'ALL' || a.status === filterStatus
  )

  // Group by originating meeting
  const grouped: Record<string, { title: string; date: string | null; items: ActionItem[] }> = {}
  filtered.forEach((a) => {
    const key = a.originating_meeting_id
    if (!grouped[key]) {
      grouped[key] = {
        title: a.originating_meeting_title || key.slice(0, 8),
        date: a.originating_meeting_date,
        items: [],
      }
    }
    grouped[key].items.push(a)
  })

  return (
    <div style={{ maxWidth: 1040 }}>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>Cross-Meeting Action Items</h1>
        <p className="text-muted text-xs mt-1">
          Persistent action item registry tracking task lifecycle across meetings (Phase 6).
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid-4 mb-6">
        {Object.entries(statusCounts).map(([s, n]) => (
          <div
            key={s}
            className="metric-card"
            style={{
              cursor: 'pointer',
              border: filterStatus === s ? '1px solid var(--accent)' : undefined,
            }}
            onClick={() => setFilterStatus(filterStatus === s ? 'ALL' : s)}
          >
            <div className="metric-label">{s.replace('_', ' ')}</div>
            <div className="metric-value">{n}</div>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-4">
        {['ALL', 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED'].map((st) => (
          <button
            key={st}
            className={`btn btn-xs ${filterStatus === st ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilterStatus(st)}
          >
            {st.replace('_', ' ')}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-muted text-xs">Loading cross-meeting actions...</div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="card text-center p-6 text-muted text-xs">No action items found.</div>
      ) : (
        Object.entries(grouped).map(([meetingId, group]) => (
          <div key={meetingId} className="card mb-4">
            <div className="flex items-center justify-between mb-3 pb-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <div>
                <span style={{ fontWeight: 700, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                  From Meeting: {group.title}
                </span>
                {group.date && (
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 8 }}>
                    ({group.date})
                  </span>
                )}
              </div>
              <span className="badge badge-purple" style={{ fontSize: 10 }}>
                {group.items.length} item{group.items.length !== 1 ? 's' : ''}
              </span>
            </div>

            <div className="flex flex-col gap-3">
              {group.items.map((a) => (
                <div key={a.id} className="action-card" style={{ padding: '12px 14px' }}>
                  <span style={{ fontSize: 18 }}>⚡</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 6, color: 'var(--text-primary)' }}>
                      {a.task}
                    </div>
                    <div className="flex gap-2 flex-wrap items-center">
                      <select
                        value={a.status}
                        onChange={(e) => handleStatusChange(a.id, e.target.value)}
                        style={{
                          background: 'var(--bg-elevated)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--radius-sm)',
                          color: 'var(--text-primary)',
                          fontSize: 10,
                          padding: '2px 6px',
                        }}
                      >
                        <option value="PENDING">PENDING</option>
                        <option value="IN_PROGRESS">IN_PROGRESS</option>
                        <option value="COMPLETED">COMPLETED</option>
                        <option value="BLOCKED">BLOCKED</option>
                        <option value="CANCELLED">CANCELLED</option>
                      </select>
                      <span className={`badge ${statusBadgeClass(a.status)}`}>{a.status}</span>
                      {a.owner_name ? (
                        <span className="badge badge-blue">👤 {a.owner_name}</span>
                      ) : (
                        <span className="badge badge-red">No owner</span>
                      )}
                      {a.deadline ? (
                        <span className="badge badge-yellow">Due {a.deadline}</span>
                      ) : (
                        <span className="badge badge-gray">No deadline</span>
                      )}
                      <span className="badge badge-gray">Priority: {a.priority}</span>
                      {a.last_updated_meeting_id && a.last_updated_meeting_id !== a.originating_meeting_id && (
                        <span className="badge badge-green" style={{ fontSize: 10 }}>
                          Updated by: {a.last_updated_meeting_title || a.last_updated_meeting_id.slice(0, 8)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'right' }}>
                    {a.evidence_count} evidence items
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
