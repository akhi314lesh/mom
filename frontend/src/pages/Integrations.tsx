import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface CalendarAttendee {
  name: string
  email: string
  response_status: string
}

interface CalendarEvent {
  id: string
  provider: string
  title: string
  description: string
  start_time: string
  end_time: string
  attendees: CalendarAttendee[]
  location?: string
  meeting_link?: string
  status: string
}

export default function Integrations() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<'calendar' | 'tasks'>('calendar')
  const [settings, setSettings] = useState<any>(null)
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [importingId, setImportingId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ provider: string; message: string; success: boolean } | null>(null)

  // Fetch settings & upcoming events
  useEffect(() => {
    fetchSettings()
    fetchEvents()
  }, [])

  async function fetchSettings() {
    try {
      const res = await fetch('http://localhost:8000/api/integrations/settings')
      if (res.ok) {
        const data = await res.json()
        setSettings(data)
      }
    } catch {
      // Backend not running
    }
  }

  async function fetchEvents() {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/integrations/calendar/events')
      if (res.ok) {
        const data = await res.json()
        setEvents(data)
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false)
    }
  }

  async function testConnection(provider: string) {
    try {
      const res = await fetch(`http://localhost:8000/api/integrations/test/${provider}`, {
        method: 'POST',
      })
      const data = await res.json()
      if (res.ok && data.connected) {
        setTestResult({
          provider,
          message: data.message || `Connected to ${provider} successfully!`,
          success: true,
        })
      } else {
        setTestResult({
          provider,
          message: data.detail || `Failed to connect to ${provider}`,
          success: false,
        })
      }
    } catch (e: any) {
      setTestResult({
        provider,
        message: e.message || 'Connection test failed',
        success: false,
      })
    }
  }

  async function handleImportMeeting(eventId: string) {
    setImportingId(eventId)
    try {
      const res = await fetch('http://localhost:8000/api/integrations/calendar/import-meeting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: eventId,
          auto_generate_brief: true,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.meeting?.id) {
          navigate(`/meetings/${data.meeting.id}`)
        }
      }
    } catch (e) {
      console.error(e)
    } finally {
      setImportingId(null)
    }
  }

  return (
    <div style={{ maxWidth: 1040, margin: '0 auto' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>External Integrations</h1>
          <p className="text-muted text-xs mt-1">
            Bi-directional calendar synchronization, pre-meeting briefs, and task exports to Jira, GitHub, and Linear.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setActiveTab('calendar')}
            className={`btn btn-sm ${activeTab === 'calendar' ? 'btn-primary' : 'btn-secondary'}`}
          >
            📅 Calendar Sync
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`btn btn-sm ${activeTab === 'tasks' ? 'btn-primary' : 'btn-secondary'}`}
          >
            ⚡ Task Trackers
          </button>
        </div>
      </div>

      {/* Connection Test Notification Banner */}
      {testResult && (
        <div
          style={{
            padding: '12px 16px',
            marginBottom: 20,
            borderRadius: 'var(--radius-md)',
            background: testResult.success ? 'rgba(34, 197, 94, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            border: `1px solid ${testResult.success ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ fontSize: 'var(--text-sm)', color: testResult.success ? '#4ade80' : '#f87171' }}>
            <strong>{testResult.success ? '✓ Verified' : '✕ Error'}:</strong> {testResult.message}
          </div>
          <button
            onClick={() => setTestResult(null)}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* ── CALENDAR TAB ── */}
      {activeTab === 'calendar' && (
        <div>
          {/* Provider Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
            {/* Google Calendar */}
            <div className="card" style={{ padding: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 8,
                      background: 'rgba(59, 130, 246, 0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#60a5fa',
                      fontWeight: 700,
                    }}
                  >
                    G
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Google Calendar</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Calendar API v3</div>
                  </div>
                </div>
                <span className="badge badge-green">Ready · Sandbox</span>
              </div>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 16 }}>
                Auto-syncs upcoming meetings, resolves attendees to known participants, and prepares pre-meeting briefs.
              </p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => testConnection('google')} className="btn btn-secondary btn-sm" style={{ flex: 1 }}>
                  Test API
                </button>
                <button onClick={fetchEvents} className="btn btn-primary btn-sm" style={{ flex: 1 }}>
                  Sync Now
                </button>
              </div>
            </div>

            {/* Microsoft Outlook */}
            <div className="card" style={{ padding: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 8,
                      background: 'rgba(14, 165, 233, 0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#38bdf8',
                      fontWeight: 700,
                    }}
                  >
                    O
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Microsoft Outlook</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Microsoft Graph API</div>
                  </div>
                </div>
                <span className="badge badge-blue">Ready · Sandbox</span>
              </div>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 16 }}>
                Integrates Office 365 / Teams calendars. Generates contextual agendas and tracks open carryover action items.
              </p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => testConnection('outlook')} className="btn btn-secondary btn-sm" style={{ flex: 1 }}>
                  Test API
                </button>
                <button onClick={fetchEvents} className="btn btn-primary btn-sm" style={{ flex: 1 }}>
                  Sync Now
                </button>
              </div>
            </div>
          </div>

          {/* Upcoming Events Section */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 600 }}>Upcoming Synchronized Meetings</h3>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  Click "Import & Generate Brief" to create an active meeting and compute pre-meeting intelligence.
                </p>
              </div>
              <button onClick={fetchEvents} className="btn btn-secondary btn-sm" disabled={loading}>
                {loading ? 'Refreshing...' : '↻ Refresh Feed'}
              </button>
            </div>

            {events.length === 0 ? (
              <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                No upcoming calendar events detected. Try clicking "Sync Now".
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {events.map((ev) => (
                  <div
                    key={ev.id}
                    style={{
                      padding: '14px 18px',
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ maxWidth: '65%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span className={`badge ${ev.provider === 'google' ? 'badge-blue' : 'badge-purple'}`}>
                          {ev.provider.toUpperCase()}
                        </span>
                        <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                          {ev.title}
                        </div>
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 6 }}>
                        🕒 {new Date(ev.start_time).toLocaleString()} · {ev.location || 'Virtual'}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {ev.attendees.map((att, idx) => (
                          <span
                            key={idx}
                            style={{
                              fontSize: 10,
                              background: 'var(--bg-card)',
                              padding: '2px 8px',
                              borderRadius: 12,
                              color: 'var(--text-secondary)',
                              border: '1px solid var(--border)',
                            }}
                          >
                            👤 {att.name}
                          </span>
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={() => handleImportMeeting(ev.id)}
                      disabled={importingId === ev.id}
                      className="btn btn-primary btn-sm"
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      {importingId === ev.id ? 'Importing...' : '📋 Import & Generate Brief'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TASKS TAB ── */}
      {activeTab === 'tasks' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 18 }}>
          {/* Jira Integration Card */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 8,
                    background: 'rgba(59, 130, 246, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#3b82f6',
                    fontWeight: 700,
                  }}
                >
                  J
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Atlassian Jira</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Enterprise Issue Tracking</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge badge-green">Ready</span>
                <button onClick={() => testConnection('jira')} className="btn btn-secondary btn-sm">
                  Test Connection
                </button>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Jira Host URL</label>
                <input
                  type="text"
                  readOnly
                  value={settings?.jira?.host || 'https://jira.company.com'}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-xs)',
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Default Project Key</label>
                <input
                  type="text"
                  readOnly
                  value={settings?.jira?.default_project || 'MOM'}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-xs)',
                  }}
                />
              </div>
            </div>
          </div>

          {/* GitHub Issues Card */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 8,
                    background: 'rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#ffffff',
                    fontWeight: 700,
                  }}
                >
                  🐙
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>GitHub Issues</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Native Repository Tasks</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge badge-green">Connected · akhi314lesh/mom</span>
                <button onClick={() => testConnection('github')} className="btn btn-secondary btn-sm">
                  Test Connection
                </button>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Repository</label>
                <input
                  type="text"
                  readOnly
                  value={settings?.github?.repository || 'akhi314lesh/mom'}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-xs)',
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Default Issue Labels</label>
                <input
                  type="text"
                  readOnly
                  value="action-item, meeting-intelligence"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-xs)',
                  }}
                />
              </div>
            </div>
          </div>

          {/* Linear Card */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 8,
                    background: 'rgba(99, 102, 241, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#818cf8',
                    fontWeight: 700,
                  }}
                >
                  L
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Linear</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Linear GraphQL Client</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge badge-purple">Ready</span>
                <button onClick={() => testConnection('linear')} className="btn btn-secondary btn-sm">
                  Test Connection
                </button>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Linear Workspace Team</label>
                <input
                  type="text"
                  readOnly
                  value={settings?.linear?.team_key || 'MOM'}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-xs)',
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Priority Auto-Mapping</label>
                <input
                  type="text"
                  readOnly
                  value="HIGH -> Urgent(1), MED -> Normal(2), LOW -> Low(3)"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-xs)',
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
