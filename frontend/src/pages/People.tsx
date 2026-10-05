import { useState, useEffect } from 'react'

interface ParticipantDirectoryItem {
  id: string
  name: string
  role: string
  email?: string
  aliases: string[]
  meetings_count: number
  total_speaking_time_ms: number
  total_speaking_time_min: number
  open_actions_count: number
  completed_actions_count: number
  resolved_speaker_labels: string[]
}

interface ParticipantHistory {
  id: string
  name: string
  role: string
  meetings_attended: Array<{ id: string; title: string; date: string; lifecycle_status: string }>
  actions_assigned: Array<{ id: string; task: string; status: string; priority: string; deadline: string | null }>
}

export default function People() {
  const [directory, setDirectory] = useState<ParticipantDirectoryItem[]>([])
  const [selectedPerson, setSelectedPerson] = useState<ParticipantHistory | null>(null)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  const fetchDirectory = async () => {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/people/directory')
      if (res.ok) {
        const data = await res.json()
        setDirectory(data || [])
      }
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    fetchDirectory()
  }, [])

  const handleSelectPerson = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/people/${id}/history`)
      if (res.ok) {
        const data = await res.json()
        setSelectedPerson(data)
      }
    } catch {}
  }

  const filtered = directory.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.role.toLowerCase().includes(search.toLowerCase())
  )

  const totalSpeakingTime = directory.reduce((acc, p) => acc + p.total_speaking_time_min, 0)
  const totalCompletedActions = directory.reduce((acc, p) => acc + p.completed_actions_count, 0)
  const totalOpenActions = directory.reduce((acc, p) => acc + p.open_actions_count, 0)

  return (
    <div style={{ maxWidth: 1040 }}>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>People & Cross-Meeting Intelligence</h1>
        <p className="text-muted text-xs mt-1">
          Organizational participants, cross-meeting speaking metrics, and assigned action item tracking (Phase 6).
        </p>
      </div>

      {/* Metric Cards */}
      <div className="grid-4 mb-6">
        <div className="metric-card">
          <div className="metric-label">TOTAL MEMBERS</div>
          <div className="metric-value">{directory.length}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">TOTAL SPEAKING TIME</div>
          <div className="metric-value">{Math.round(totalSpeakingTime)}m</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">OPEN TASKS</div>
          <div className="metric-value" style={{ color: 'var(--accent)' }}>
            {totalOpenActions}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">COMPLETED TASKS</div>
          <div className="metric-value" style={{ color: 'var(--success)' }}>
            {totalCompletedActions}
          </div>
        </div>
      </div>

      {/* Search Input */}
      <div className="mb-4">
        <input
          type="text"
          className="input"
          placeholder="Search participants by name or role..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            width: '100%',
            padding: '8px 12px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
            fontSize: 'var(--text-xs)',
          }}
        />
      </div>

      {/* Directory Grid */}
      {loading ? (
        <div className="text-muted text-xs">Loading organizational participants...</div>
      ) : filtered.length === 0 ? (
        <div className="card text-center p-6 text-muted text-xs">No participants found.</div>
      ) : (
        <div className="grid-2 gap-4">
          {filtered.map((person) => (
            <div
              key={person.id}
              className="card"
              style={{
                cursor: 'pointer',
                transition: 'border-color 0.2s',
                border: selectedPerson?.id === person.id ? '1px solid var(--accent)' : '1px solid var(--border)',
              }}
              onClick={() => handleSelectPerson(person.id)}
            >
            <div className="flex items-center gap-3 mb-3">
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: '50%',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 16,
                  color: 'var(--accent)',
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                {person.name.charAt(0)}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                  {person.name}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  {person.role || 'Team Member'}
                </div>
              </div>
              <span className="badge badge-blue" style={{ fontSize: 10 }}>
                {person.meetings_count} meeting{person.meetings_count !== 1 ? 's' : ''}
              </span>
            </div>

            <div className="flex gap-2 flex-wrap items-center pt-2" style={{ borderTop: '1px solid var(--border-subtle)', fontSize: 10 }}>
              <span className="badge badge-gray">🎙️ {person.total_speaking_time_min} mins spoken</span>
              {person.open_actions_count > 0 && (
                <span className="badge badge-yellow">⚡ {person.open_actions_count} open task{person.open_actions_count !== 1 ? 's' : ''}</span>
              )}
              {person.completed_actions_count > 0 && (
                <span className="badge badge-green">✓ {person.completed_actions_count} done</span>
              )}
              {person.resolved_speaker_labels.length > 0 && (
                <span className="badge badge-purple" style={{ marginLeft: 'auto' }}>
                  {person.resolved_speaker_labels.join(', ')}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
      )}

      {/* Selected Person History Drawer */}
      {selectedPerson && (
        <div
          style={{
            position: 'fixed',
            right: 0,
            top: 0,
            bottom: 0,
            width: 440,
            background: 'var(--bg-card)',
            borderLeft: '1px solid var(--border)',
            boxShadow: 'var(--shadow-xl)',
            padding: 24,
            overflowY: 'auto',
            zIndex: 1000,
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <div style={{ fontWeight: 700, fontSize: 'var(--text-lg)', color: 'var(--text-primary)' }}>
                {selectedPerson.name}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                {selectedPerson.role}
              </div>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedPerson(null)}
              style={{ padding: '4px 8px' }}
            >
              ✕ Close
            </button>
          </div>

          {/* Meetings History */}
          <div className="mb-6">
            <div style={{ fontWeight: 600, fontSize: 'var(--text-xs)', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
              Meetings Attended ({selectedPerson.meetings_attended.length})
            </div>
            {selectedPerson.meetings_attended.length === 0 ? (
              <div className="text-muted text-xs">No meetings recorded yet.</div>
            ) : (
              <div className="flex flex-col gap-2">
                {selectedPerson.meetings_attended.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      padding: '8px 10px',
                      background: 'var(--bg-elevated)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)',
                      fontSize: 'var(--text-xs)',
                    }}
                  >
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{m.title}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 10, marginTop: 2 }}>{m.date}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action Items History */}
          <div>
            <div style={{ fontWeight: 600, fontSize: 'var(--text-xs)', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
              Assigned Tasks Across Meetings ({selectedPerson.actions_assigned.length})
            </div>
            {selectedPerson.actions_assigned.length === 0 ? (
              <div className="text-muted text-xs">No tasks assigned.</div>
            ) : (
              <div className="flex flex-col gap-2">
                {selectedPerson.actions_assigned.map((a) => (
                  <div
                    key={a.id}
                    style={{
                      padding: '8px 10px',
                      background: 'var(--bg-elevated)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)',
                      fontSize: 'var(--text-xs)',
                    }}
                  >
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                      {a.task}
                    </div>
                    <div className="flex gap-2 items-center" style={{ fontSize: 10 }}>
                      <span className={`badge ${a.status === 'COMPLETED' ? 'badge-green' : 'badge-yellow'}`}>
                        {a.status}
                      </span>
                      {a.deadline && <span style={{ color: 'var(--text-muted)' }}>Due: {a.deadline}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
