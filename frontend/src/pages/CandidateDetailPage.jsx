import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'
import Topbar from '../components/Topbar'
import { useAuth } from '../components/AuthContext'

const CATEGORIES = [
  'Technical Skills', 'Problem Solving', 'Communication',
  'Culture Fit', 'System Design', 'Leadership',
]

function StarSelect({ value, onChange }) {
  const [hovered, setHovered] = useState(0)
  return (
    <div className="star-select">
      {[1, 2, 3, 4, 5].map(n => (
        <span
          key={n}
          className={`star ${n <= (hovered || value) ? 'active' : ''}`}
          onMouseEnter={() => setHovered(n)}
          onMouseLeave={() => setHovered(0)}
          onClick={() => onChange(n)}
        >★</span>
      ))}
    </div>
  )
}

export default function CandidateDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [candidate, setCandidate] = useState(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')

  // Scoring form
  const [scoreForm, setScoreForm]   = useState({ category: CATEGORIES[0], score: 0, note: '' })
  const [scoreError, setScoreError] = useState('')
  const [scoreOk, setScoreOk]       = useState('')
  const [scoring, setScoring]       = useState(false)

  // AI summary
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError]     = useState('')

  // Admin notes
  const [notes, setNotes]       = useState('')
  const [notesOk, setNotesOk]   = useState('')
  const [notesErr, setNotesErr] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const data = await api.getCandidate(id)
      setCandidate(data)
      setNotes(data.internal_notes || '')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  async function handleScore(e) {
    e.preventDefault()
    if (!scoreForm.score) { setScoreError('Please select a score'); return }
    setScoreError('')
    setScoreOk('')
    setScoring(true)
    try {
      await api.submitScore(id, scoreForm)
      setScoreOk('Score submitted!')
      setScoreForm({ category: CATEGORIES[0], score: 0, note: '' })
      await load()
      setTimeout(() => setScoreOk(''), 3000)
    } catch (e) {
      setScoreError(e.message)
    } finally {
      setScoring(false)
    }
  }

  async function handleSummary() {
    setSummaryLoading(true)
    setSummaryError('')
    try {
      await api.generateSummary(id)
      await load()
    } catch (e) {
      setSummaryError(e.message)
    } finally {
      setSummaryLoading(false)
    }
  }

  async function handleSaveNotes() {
    setSavingNotes(true)
    setNotesOk('')
    setNotesErr('')
    try {
      await api.updateNotes(id, notes)
      setNotesOk('Notes saved')
      setTimeout(() => setNotesOk(''), 3000)
    } catch (e) {
      setNotesErr(e.message)
    } finally {
      setSavingNotes(false)
    }
  }

  async function handleDelete() {
    if (!confirm('Archive this candidate? This cannot be undone.')) return
    try {
      await api.deleteCandidate(id)
      navigate('/candidates')
    } catch (e) {
      setError(e.message)
    }
  }

  if (loading) return (
    <div className="layout">
      <Topbar />
      <div className="page-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
        <div className="spinner" style={{ width: 32, height: 32 }} />
      </div>
    </div>
  )

  if (error || !candidate) return (
    <div className="layout">
      <Topbar />
      <div className="page-content">
        <div className="error-box">{error || 'Candidate not found'}</div>
        <Link to="/candidates" className="btn" style={{ marginTop: 16 }}>← Back</Link>
      </div>
    </div>
  )

  return (
    <div className="layout">
      <Topbar />
      <div className="page-content">
        {/* Header */}
        <div className="detail-header">
          <Link to="/candidates" className="btn btn-ghost btn-sm" style={{ marginBottom: 16 }}>← All Candidates</Link>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <h1 className="detail-name">{candidate.name}</h1>
              <div className="detail-meta">
                <span>{candidate.email}</span>
                <span>·</span>
                <span>{candidate.role_applied}</span>
                <span className={`status-badge status-${candidate.status}`}>{candidate.status}</span>
              </div>
              <div style={{ marginTop: 8 }}>
                {candidate.skills.map(s => <span key={s} className="skill-tag">{s}</span>)}
              </div>
            </div>
            {user.role === 'admin' && (
              <button className="btn btn-danger btn-sm" onClick={handleDelete}>Archive</button>
            )}
          </div>
        </div>

        <div className="detail-grid">
          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Profile info */}
            <div className="card">
              <div className="section-title">Profile</div>
              <div className="info-row">
                <span className="info-label">Applied for</span>
                <span className="info-value">{candidate.role_applied}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Status</span>
                <span className="info-value">
                  <span className={`status-badge status-${candidate.status}`}>{candidate.status}</span>
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Added</span>
                <span className="info-value">{new Date(candidate.created_at).toLocaleDateString()}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Scores</span>
                <span className="info-value">{candidate.scores.length}</span>
              </div>
            </div>

            {/* Admin internal notes */}
            {user.role === 'admin' && (
              <div className="admin-panel">
                <div className="section-title" style={{ color: 'rgba(240,195,48,.7)' }}>Admin Notes</div>
                {notesOk && <div className="toast toast-success" style={{ marginBottom: 10 }}>{notesOk}</div>}
                {notesErr && <div className="toast toast-error" style={{ marginBottom: 10 }}>{notesErr}</div>}
                <textarea
                  className="input notes-textarea"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  placeholder="Internal notes (not visible to reviewers)…"
                />
                <button
                  className="btn btn-sm btn-primary"
                  style={{ marginTop: 8 }}
                  onClick={handleSaveNotes}
                  disabled={savingNotes}
                >
                  {savingNotes ? 'Saving…' : 'Save Notes'}
                </button>
              </div>
            )}
          </div>

          {/* Right column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* AI Summary */}
            <div className="card">
              <div className="section-title">AI Summary</div>
              {summaryLoading ? (
                <div className="ai-loading">
                  <div className="spinner" />
                  <span>Generating summary — this takes a moment…</span>
                </div>
              ) : summaryError ? (
                <div className="error-box">{summaryError}</div>
              ) : candidate.ai_summary ? (
                <div className="ai-box">{candidate.ai_summary}</div>
              ) : (
                <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 12 }}>
                  No summary generated yet.
                </div>
              )}
              {!summaryLoading && (
                <button
                  className="btn btn-sm"
                  style={{ marginTop: 12 }}
                  onClick={handleSummary}
                  disabled={summaryLoading}
                >
                  {candidate.ai_summary ? '↺ Regenerate Summary' : '✦ Generate AI Summary'}
                </button>
              )}
            </div>

            {/* Scores */}
            <div className="card">
              <div className="section-title">
                Scores {user.role === 'reviewer' && '(yours)'}
              </div>
              {candidate.scores.length === 0 ? (
                <p style={{ color: 'var(--muted)', fontSize: 13 }}>No scores yet.</p>
              ) : (
                candidate.scores.map(s => (
                  <div key={s.id} className="score-row">
                    <span className={`score-circle score-${s.score}`}>{s.score}</span>
                    <div style={{ flex: 1 }}>
                      <div className="score-category">{s.category}</div>
                      {s.note && <div className="score-note">{s.note}</div>}
                    </div>
                    <span style={{ color: 'var(--muted)', fontSize: 11 }}>
                      {new Date(s.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))
              )}
            </div>

            {/* Submit score */}
            <div className="card">
              <div className="section-title">Add Score</div>
              {scoreOk && <div className="toast toast-success" style={{ marginBottom: 12 }}>{scoreOk}</div>}
              {scoreError && <div className="toast toast-error" style={{ marginBottom: 12 }}>{scoreError}</div>}
              <form onSubmit={handleScore}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                  <div>
                    <label>Category</label>
                    <select
                      className="input"
                      value={scoreForm.category}
                      onChange={e => setScoreForm(f => ({ ...f, category: e.target.value }))}
                    >
                      {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label>Score</label>
                    <StarSelect
                      value={scoreForm.score}
                      onChange={v => setScoreForm(f => ({ ...f, score: v }))}
                    />
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label>Note (optional)</label>
                  <input
                    className="input"
                    value={scoreForm.note}
                    onChange={e => setScoreForm(f => ({ ...f, note: e.target.value }))}
                    placeholder="Brief justification…"
                  />
                </div>
                <button className="btn btn-primary btn-sm" type="submit" disabled={scoring}>
                  {scoring ? 'Submitting…' : 'Submit Score'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}