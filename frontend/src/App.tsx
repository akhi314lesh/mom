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
            <div key={i} className="sidebar-section">{item.section}</div>
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
          Phase 8 · External Integrations
        </div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 2 }}>
          Calendar Sync · Pre-Meeting Briefs · Task Export
        </div>
      </div>
    </nav>
  )
}

function TopBar() {
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
      <div className="top-bar-right">
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
        <TopBar />
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
