import { useState, useEffect } from 'react'

interface KnowledgeItem {
  id: string
  type: string
  content: string
  confidence: number
  verified: boolean
  verification_source: string
  source_meeting_ids: string[]
  source_meetings_count: number
  created_at?: string
}

interface TerminologyItem {
  id: string
  term: string
  canonical_meaning: string
  aliases: string[]
  verified: boolean
  confidence: number
  source_meeting_ids: string[]
  source_meetings_count: number
}

interface CrossMeetingAction {
  id: string
  task: string
  status: string
  priority: string
  deadline: string | null
  confidence: number
  owner_name: string | null
  originating_meeting_id: string
  originating_meeting_title: string
  originating_meeting_date: string | null
  last_updated_meeting_id: string | null
  last_updated_meeting_title: string | null
  evidence_count: number
}

interface CrossMeetingContradiction {
  id: string
  description: string
  contradiction_type: string
  confidence: number
  review_state: string
  meeting_a_id: string
  meeting_a_title: string
  meeting_b_id: string
  meeting_b_title: string
}

type TabType = 'KNOWLEDGE' | 'TERMINOLOGY' | 'ACTIONS' | 'CONTRADICTIONS'

export default function Knowledge() {
  const [activeTab, setActiveTab] = useState<TabType>('KNOWLEDGE')
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('ALL')

  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [terms, setTerms] = useState<TerminologyItem[]>([])
  const [actions, setActions] = useState<CrossMeetingAction[]>([])
  const [contradictions, setContradictions] = useState<CrossMeetingContradiction[]>([])
  const [loading, setLoading] = useState(false)

  // New item modal states
  const [showAddKnowledge, setShowAddKnowledge] = useState(false)
  const [newKType, setNewKType] = useState('FACT')
  const [newKContent, setNewKContent] = useState('')

  const [showAddTerm, setShowAddTerm] = useState(false)
  const [newTerm, setNewTerm] = useState('')
  const [newTermMeaning, setNewTermMeaning] = useState('')
  const [newTermAliases, setNewTermAliases] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const [kRes, tRes, aRes, cRes] = await Promise.all([
        fetch('http://localhost:8000/api/knowledge/items').then((r) => (r.ok ? r.json() : [])),
        fetch('http://localhost:8000/api/knowledge/terminology').then((r) => (r.ok ? r.json() : [])),
        fetch('http://localhost:8000/api/continuity/actions').then((r) => (r.ok ? r.json() : [])),
        fetch('http://localhost:8000/api/knowledge/contradictions').then((r) => (r.ok ? r.json() : [])),
      ])
      setItems(kRes || [])
      setTerms(tRes || [])
      setActions(aRes || [])
      setContradictions(cRes || [])
    } catch {
      // Fallback
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleVerifyKnowledge = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/knowledge/items/${id}/verify`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verified: true }),
      })
      if (res.ok) {
        setItems((prev) =>
          prev.map((k) => (k.id === id ? { ...k, verified: true, verification_source: 'HUMAN', confidence: 1.0 } : k))
        )
      }
    } catch {}
  }

  const handleVerifyTerm = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/knowledge/terminology/${id}/verify`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verified: true }),
      })
      if (res.ok) {
        setTerms((prev) =>
          prev.map((t) => (t.id === id ? { ...t, verified: true, confidence: 1.0 } : t))
        )
      }
    } catch {}
  }

  const handleCreateKnowledge = async () => {
    if (!newKContent.trim()) return
    try {
      const res = await fetch('http://localhost:8000/api/knowledge/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: newKType, content: newKContent }),
      })
      if (res.ok) {
        setShowAddKnowledge(false)
        setNewKContent('')
        fetchData()
      }
    } catch {}
  }

  const handleCreateTerm = async () => {
    if (!newTerm.trim()) return
    const aliases = newTermAliases
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    try {
      const res = await fetch('http://localhost:8000/api/knowledge/terminology', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term: newTerm, canonical_meaning: newTermMeaning, aliases }),
      })
      if (res.ok) {
        setShowAddTerm(false)
        setNewTerm('')
        setNewTermMeaning('')
        setNewTermAliases('')
        fetchData()
      }
    } catch {}
  }

  const handleUpdateActionStatus = async (actionId: string, newStatus: string) => {
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

  // Filtered views
  const filteredKnowledge = items.filter((k) => {
    const matchesSearch = k.content.toLowerCase().includes(search.toLowerCase())
    const matchesType = filterType === 'ALL' || k.type === filterType
    return matchesSearch && matchesType
  })

  const filteredTerms = terms.filter(
    (t) =>
      t.term.toLowerCase().includes(search.toLowerCase()) ||
      t.canonical_meaning.toLowerCase().includes(search.toLowerCase())
  )

  const filteredActions = actions.filter((a) =>
    a.task.toLowerCase().includes(search.toLowerCase()) ||
    (a.owner_name && a.owner_name.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div style={{ maxWidth: 1040 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>Organizational Memory & Continuity</h1>
          <p className="text-muted text-xs mt-1">
            Persistent cross-meeting knowledge, terminology dictionary, and cross-meeting action lineage (Phase 6).
          </p>
        </div>
        <div className="flex gap-2">
          {activeTab === 'KNOWLEDGE' && (
            <button className="btn btn-primary btn-sm" onClick={() => setShowAddKnowledge(true)}>
              + Add Knowledge Item
            </button>
          )}
          {activeTab === 'TERMINOLOGY' && (
            <button className="btn btn-primary btn-sm" onClick={() => setShowAddTerm(true)}>
              + Add Term
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs mb-6" style={{ borderBottom: '1px solid var(--border)' }}>
        <button
          className={`tab-btn ${activeTab === 'KNOWLEDGE' ? 'active' : ''}`}
          onClick={() => setActiveTab('KNOWLEDGE')}
        >
          🧠 Knowledge Base ({items.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'TERMINOLOGY' ? 'active' : ''}`}
          onClick={() => setActiveTab('TERMINOLOGY')}
        >
          📖 Terminology ({terms.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'ACTIONS' ? 'active' : ''}`}
          onClick={() => setActiveTab('ACTIONS')}
        >
          ⚡ Cross-Meeting Actions ({actions.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'CONTRADICTIONS' ? 'active' : ''}`}
          onClick={() => setActiveTab('CONTRADICTIONS')}
        >
          ⚠️ Decision Reversals ({contradictions.length})
        </button>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="flex items-center gap-3 mb-6">
        <input
          type="text"
          className="input flex-1"
          placeholder={`Search ${activeTab.toLowerCase()}...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
            fontSize: 'var(--text-xs)',
          }}
        />
        {activeTab === 'KNOWLEDGE' && (
          <div className="flex gap-1">
            {['ALL', 'FACT', 'DECISION', 'PATTERN', 'PROJECT'].map((t) => (
              <button
                key={t}
                className={`btn btn-xs ${filterType === t ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setFilterType(t)}
                style={{ fontSize: 10, padding: '4px 8px' }}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Tab 1: KNOWLEDGE */}
      {activeTab === 'KNOWLEDGE' && (
        <div>
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              fontSize: 'var(--text-xs)',
              color: 'var(--text-muted)',
              marginBottom: 16,
            }}
          >
            🛡️ <strong>Strict Verification Invariant:</strong> Items marked <code>INFERRED</code> are NEVER promoted to verified without human confirmation. System confidence ≥ 85% is required for automatic system verification.
          </div>

          {loading ? (
            <div className="text-muted text-xs">Loading organizational memory...</div>
          ) : filteredKnowledge.length === 0 ? (
            <div className="card text-center p-6 text-muted text-xs">No knowledge items match your search.</div>
          ) : (
            <div className="grid-2 gap-4">
              {filteredKnowledge.map((item) => (
                <div key={item.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="badge badge-blue" style={{ fontSize: 10 }}>
                      {item.type}
                    </span>
                    {item.verified ? (
                      <span className="badge badge-green" style={{ fontSize: 10 }}>
                        ✓ {item.verification_source === 'HUMAN' ? 'Human Verified' : 'System Verified'}
                      </span>
                    ) : (
                      <span className="badge badge-yellow" style={{ fontSize: 10 }}>
                        Inferred
                      </span>
                    )}
                    <span
                      style={{
                        marginLeft: 'auto',
                        fontSize: 10,
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {Math.round(item.confidence * 100)}%
                    </span>
                  </div>

                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)', flex: 1 }}>
                    {item.content}
                  </div>

                  <div
                    className="flex items-center justify-between"
                    style={{
                      marginTop: 12,
                      paddingTop: 8,
                      borderTop: '1px solid var(--border-subtle)',
                      fontSize: 10,
                      color: 'var(--text-muted)',
                    }}
                  >
                    <span>
                      {item.source_meetings_count} meeting{item.source_meetings_count !== 1 ? 's' : ''} source
                    </span>
                    {!item.verified && (
                      <button
                        className="btn btn-secondary btn-xs"
                        style={{ fontSize: 10, padding: '2px 8px' }}
                        onClick={() => handleVerifyKnowledge(item.id)}
                      >
                        ✓ Confirm Fact
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: TERMINOLOGY */}
      {activeTab === 'TERMINOLOGY' && (
        <div>
          {loading ? (
            <div className="text-muted text-xs">Loading terminology dictionary...</div>
          ) : filteredTerms.length === 0 ? (
            <div className="card text-center p-6 text-muted text-xs">No terminology entries found.</div>
          ) : (
            <div className="grid-2 gap-4">
              {filteredTerms.map((t) => (
                <div key={t.id} className="card">
                  <div className="flex items-center gap-2 mb-2">
                    <span style={{ fontWeight: 700, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                      {t.term}
                    </span>
                    {t.verified ? (
                      <span className="badge badge-green" style={{ fontSize: 10 }}>
                        ✓ Verified
                      </span>
                    ) : (
                      <span className="badge badge-yellow" style={{ fontSize: 10 }}>
                        Unverified
                      </span>
                    )}
                    <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>
                      {t.source_meetings_count} meeting{t.source_meetings_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                    {t.canonical_meaning}
                  </div>
                  {t.aliases.length > 0 && (
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
                      Aliases: {t.aliases.join(', ')}
                    </div>
                  )}
                  {!t.verified && (
                    <div className="mt-3">
                      <button
                        className="btn btn-secondary btn-xs"
                        style={{ fontSize: 10, padding: '2px 8px' }}
                        onClick={() => handleVerifyTerm(t.id)}
                      >
                        ✓ Verify Definition
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: CROSS-MEETING ACTIONS */}
      {activeTab === 'ACTIONS' && (
        <div>
          <div className="grid-1 gap-3">
            {filteredActions.map((a) => (
              <div key={a.id} className="card" style={{ padding: '14px 16px' }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: 16 }}>⚡</span>
                    <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                      {a.task}
                    </span>
                  </div>
                  <select
                    value={a.status}
                    onChange={(e) => handleUpdateActionStatus(a.id, e.target.value)}
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
                </div>

                <div className="flex gap-2 flex-wrap items-center mt-2" style={{ fontSize: 10 }}>
                  <span className="badge badge-blue">Owner: {a.owner_name || 'Unassigned'}</span>
                  {a.deadline && <span className="badge badge-yellow">Due {a.deadline}</span>}
                  <span className="badge badge-gray">Priority: {a.priority}</span>
                  <span className="badge badge-purple">
                    From: {a.originating_meeting_title || a.originating_meeting_id.slice(0, 8)}
                  </span>
                  {a.last_updated_meeting_id && a.last_updated_meeting_id !== a.originating_meeting_id && (
                    <span className="badge badge-green">
                      Updated by: {a.last_updated_meeting_title || a.last_updated_meeting_id.slice(0, 8)}
                    </span>
                  )}
                  <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>
                    {a.evidence_count} evidence items linked
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: CONTRADICTIONS & REVERSALS */}
      {activeTab === 'CONTRADICTIONS' && (
        <div>
          {contradictions.length === 0 ? (
            <div className="card text-center p-6 text-muted text-xs">
              No cross-meeting decision reversals detected.
            </div>
          ) : (
            <div className="grid-1 gap-3">
              {contradictions.map((c) => (
                <div
                  key={c.id}
                  className="card"
                  style={{
                    borderLeft: '4px solid var(--red)',
                    padding: '14px 16px',
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="badge badge-red" style={{ fontSize: 10 }}>
                      ⚠️ Cross-Meeting Reversal
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                      Confidence: {Math.round(c.confidence * 100)}%
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                    {c.description}
                  </div>
                  <div className="flex gap-4 mt-3" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    <div>
                      Meeting A: <strong>{c.meeting_a_title || c.meeting_a_id?.slice(0, 8)}</strong>
                    </div>
                    <div>
                      Meeting B: <strong>{c.meeting_b_title || c.meeting_b_id?.slice(0, 8)}</strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Knowledge Item Modal */}
      {showAddKnowledge && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div className="card" style={{ width: 440, padding: 20 }}>
            <div style={{ fontWeight: 700, fontSize: 'var(--text-md)', marginBottom: 12 }}>
              Add Knowledge Item
            </div>
            <div className="mb-3">
              <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Type
              </label>
              <select
                value={newKType}
                onChange={(e) => setNewKType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '6px 8px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <option value="FACT">FACT</option>
                <option value="DECISION">DECISION</option>
                <option value="PATTERN">PATTERN</option>
                <option value="PROJECT">PROJECT</option>
              </select>
            </div>
            <div className="mb-4">
              <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Content
              </label>
              <textarea
                value={newKContent}
                onChange={(e) => setNewKContent(e.target.value)}
                placeholder="State the verified fact or architectural pattern..."
                rows={3}
                style={{
                  width: '100%',
                  padding: '8px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-xs)',
                }}
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button className="btn btn-secondary btn-sm" onClick={() => setShowAddKnowledge(false)}>
                Cancel
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleCreateKnowledge}>
                Save (Verified)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Term Modal */}
      {showAddTerm && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div className="card" style={{ width: 440, padding: 20 }}>
            <div style={{ fontWeight: 700, fontSize: 'var(--text-md)', marginBottom: 12 }}>
              Add Terminology Entry
            </div>
            <div className="mb-3">
              <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Term / Acronym
              </label>
              <input
                value={newTerm}
                onChange={(e) => setNewTerm(e.target.value)}
                placeholder="e.g. OODA, WASAPI, JWT"
                style={{
                  width: '100%',
                  padding: '6px 8px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-xs)',
                }}
              />
            </div>
            <div className="mb-3">
              <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Canonical Meaning
              </label>
              <textarea
                value={newTermMeaning}
                onChange={(e) => setNewTermMeaning(e.target.value)}
                placeholder="Definition of the term in organizational context..."
                rows={2}
                style={{
                  width: '100%',
                  padding: '8px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-xs)',
                }}
              />
            </div>
            <div className="mb-4">
              <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Aliases (comma-separated)
              </label>
              <input
                value={newTermAliases}
                onChange={(e) => setNewTermAliases(e.target.value)}
                placeholder="e.g. OODA loop, loopback"
                style={{
                  width: '100%',
                  padding: '6px 8px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-xs)',
                }}
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button className="btn btn-secondary btn-sm" onClick={() => setShowAddTerm(false)}>
                Cancel
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleCreateTerm}>
                Save Term
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
