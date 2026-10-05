import { useState, useEffect, useRef } from 'react'
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Meetings from './pages/Meetings'
import NewMeeting from './pages/NewMeeting'
import MeetingWorkspace from './pages/MeetingWorkspace'
import ActionItems from './pages/ActionItems'
import Decisions from './pages/Decisions'
import People from './pages/People'
import Knowledge from './pages/Knowledge'
import Settings from './pages/Settings'
import AgentConsole from './pages/AgentConsole'
import Integrations from './pages/Integrations'
import Overlay from './pages/Overlay'
import './index.css'

const NAV = [
  { section: 'WORKSPACE' },
  { path: '/', label: 'Dashboard', icon: '▦' },
  { path: '/meetings', label: 'Meetings', icon: '◉' },
  { section: 'INTELLIGENCE' },
  { path: '/decisions', label: 'Decisions', icon: '✓' },
  { path: '/actions', label: 'Action Items', icon: '⚡' },
  { path: '/people', label: 'People', icon: '◎' },
  { path: '/knowledge', label: 'Knowledge', icon: '◈' },
  { section: 'SYSTEM' },
  { path: '/integrations', label: 'Integrations', icon: '🔌' },
  { path: '/agent', label: 'Agent Console', icon: '⌬' },
  { path: '/settings', label: 'Settings', icon: '◌' },
]

function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark">M</div>
        <div>
          <div className="sidebar-logo-text">MOM for meetings</div>
          <div className="sidebar-logo-sub">Evidence Grounded</div>
        </div>
      </div>
      <div className="sidebar-nav">
        {NAV.map((item, i) =>
          'section' in item ? (
            <div key={i} className="sidebar-section">
              {item.section}
            </div>
          ) : (
            <NavLink
              key={item.path}
              to={item.path!}
              end={item.path === '/'}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <span className="nav-item-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          )
        )}
      </div>
      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
          Operational Mode
        </div>
        <div
          style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--success)',
            fontWeight: 600,
            marginTop: 2,
          }}
        >
          DEMO · Zero Config
        </div>
      </div>
    </nav>
  )
}

interface HealthData {
  status: string
  backend: string
  database: string
  storage: string
  mode: string
  llm: { provider: string; status: string }
  asr: { provider: string; status: string }
  overlay: { capability: string; port: number }
}

function StatusIndicator({
  health,
  isOffline,
  onRefresh,
}: {
  health: HealthData | null
  isOffline: boolean
  onRefresh: () => void
}) {
  const [open, setOpen] = useState(false)
  const popoverRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const dotColor = isOffline
    ? 'var(--error)'
    : health?.database === 'healthy'
    ? 'var(--success)'
    : 'var(--warning)'
  const statusLabel = isOffline
    ? 'Backend Offline'
    : health?.database === 'healthy'
    ? 'All Systems Operational'
    : 'Degraded'

  return (
    <div style={{ position: 'relative' }} ref={popoverRef}>
      <button
        onClick={() => setOpen(!open)}
        className="btn btn-secondary btn-sm flex items-center gap-2"
        style={{
          fontSize: 'var(--text-xs)',
          padding: '5px 10px',
          borderColor: isOffline ? 'rgba(239, 68, 68, 0.4)' : undefined,
        }}
        title="Click to view system health diagnostics"
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: dotColor,
            boxShadow: `0 0 6px ${dotColor}`,
            display: 'inline-block',
          }}
        />
        <span>{statusLabel}</span>
        <span style={{ fontSize: 9, opacity: 0.7 }}>▾</span>
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: 'calc(100% + 8px)',
            width: 290,
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            zIndex: 1000,
            padding: 14,
          }}
        >
          <div className="flex items-center justify-between mb-3 pb-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-primary)' }}>
              SYSTEM DIAGNOSTICS
            </div>
            <button
              onClick={onRefresh}
              className="btn btn-secondary btn-sm"
              style={{ padding: '2px 6px', fontSize: 10 }}
              title="Refresh health"
            >
              ⟳ Check
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 'var(--text-xs)' }}>
            <div className="flex items-center justify-between">
              <span className="text-muted">Backend (FastAPI)</span>
              <span style={{ color: isOffline ? 'var(--error)' : 'var(--success)', fontWeight: 600 }}>
                {isOffline ? 'Offline ✕' : 'Healthy ✓'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">Database (SQLite WAL)</span>
              <span style={{ color: health?.database === 'healthy' ? 'var(--success)' : 'var(--error)', fontWeight: 600 }}>
                {health?.database === 'healthy' ? 'Healthy ✓' : 'Unavailable ✕'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">Storage Layer</span>
              <span style={{ color: health?.storage === 'healthy' ? 'var(--success)' : 'var(--warning)', fontWeight: 600 }}>
                {health?.storage === 'healthy' ? 'Healthy ✓' : 'Degraded'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">AI Provider</span>
              <span style={{ color: 'var(--accent)', fontWeight: 600 }}>
                {health?.llm?.provider?.toUpperCase() || 'DEMO / STUB'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">ASR Pipeline</span>
              <span style={{ color: 'var(--accent)', fontWeight: 600 }}>
                {health?.asr?.provider?.toUpperCase() || 'DEMO / STUB'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">Desktop Overlay</span>
              <span style={{ color: 'var(--success)', fontWeight: 600 }}>
                Ready (Companion)
              </span>
            </div>
          </div>

          <div
            style={{
              marginTop: 12,
              paddingTop: 8,
              borderTop: '1px solid var(--border-subtle)',
              fontSize: 10,
              color: 'var(--text-muted)',
              lineHeight: 1.4,
            }}
          >
            Zero-key demo state active. No cloud keys required.
          </div>
        </div>
      )}
    </div>
  )
}

function TopBar({
  health,
  isOffline,
  onRefresh,
}: {
  health: HealthData | null
  isOffline: boolean
  onRefresh: () => void
}) {
  const location = useLocation()
  const titles: Record<string, string> = {
    '/': 'Dashboard',
    '/meetings': 'Meetings',
    '/decisions': 'Decisions',
    '/actions': 'Action Items',
    '/people': 'People',
    '/knowledge': 'Knowledge',
    '/agent': 'Agent Console',
    '/settings': 'Settings',
    '/meetings/new': 'New Meeting',
  }
  const title = titles[location.pathname] ?? 'Meeting Workspace'

  return (
    <div className="top-bar">
      <span className="top-bar-title">{title}</span>
      <div className="top-bar-right flex items-center gap-3">
        <StatusIndicator health={health} isOffline={isOffline} onRefresh={onRefresh} />
        <NavLink to="/meetings/new">
          <button className="btn btn-primary btn-sm">+ New Meeting</button>
        </NavLink>
      </div>
    </div>
  )
}

function AppContent() {
  const location = useLocation()
  const isOverlay = location.pathname.startsWith('/overlay')

  const [health, setHealth] = useState<HealthData | null>(null)
  const [isOffline, setIsOffline] = useState(false)

  const checkHealth = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/health')
      if (res.ok) {
        const data = await res.json()
        setHealth(data)
        setIsOffline(false)
      } else {
        setIsOffline(true)
      }
    } catch {
      setIsOffline(true)
    }
  }

  useEffect(() => {
    checkHealth()
    const timer = setInterval(checkHealth, 12000)
    return () => clearInterval(timer)
  }, [])

  if (isOverlay) {
    return (
      <Routes>
        <Route path="/overlay" element={<Overlay />} />
        <Route path="/overlay/:id" element={<Overlay />} />
      </Routes>
    )
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        <TopBar health={health} isOffline={isOffline} onRefresh={checkHealth} />

        {/* Backend Offline Human-Readable Banner */}
        {isOffline && (
          <div
            style={{
              margin: '16px 24px 0',
              padding: '14px 18px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 16,
            }}
          >
            <div>
              <div className="flex items-center gap-2" style={{ fontWeight: 700, color: 'var(--error)', fontSize: 'var(--text-sm)' }}>
                <span>⚠</span>
                <span>MOM BACKEND OFFLINE</span>
                <span className="badge badge-red" style={{ fontSize: 10 }}>API: localhost:8000</span>
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: 4 }}>
                <strong>Developer details:</strong> FastAPI process is not responding. Run{' '}
                <code style={{ background: 'rgba(0,0,0,0.3)', padding: '2px 5px', borderRadius: 3 }}>
                  .\scripts\start.ps1
                </code>{' '}
                or double-click{' '}
                <code style={{ background: 'rgba(0,0,0,0.3)', padding: '2px 5px', borderRadius: 3 }}>
                  START_MOM.bat
                </code>{' '}
                to start all services.
              </div>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={checkHealth} style={{ flexShrink: 0 }}>
              ⟳ Retry Connection
            </button>
          </div>
        )}

        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/meetings" element={<Meetings />} />
            <Route path="/meetings/new" element={<NewMeeting />} />
            <Route path="/meetings/:id" element={<MeetingWorkspace />} />
            <Route path="/actions" element={<ActionItems />} />
            <Route path="/decisions" element={<Decisions />} />
            <Route path="/people" element={<People />} />
            <Route path="/knowledge" element={<Knowledge />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/agent" element={<AgentConsole />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}

export default App
