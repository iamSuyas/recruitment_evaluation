import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import Topbar from '../components/Topbar'
import { useAuth } from '../components/AuthContext'

const STATUS_OPTIONS = ['', 'new', 'reviewed', 'hired', 'rejected']
const ROLE_OPTIONS   = ['', 'Backend Engineer', 'Frontend Engineer', 'Full Stack Engineer', 'DevOps Engineer']

export default function CandidateListPage() {
  const { user } = useAuth()
  const [candidates, setCandidates] = useState([])
  const [total, setTotal]   = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')

  const [filters, setFilters] = useState({
    status: '', role_applied: '', skill: '', keyword: '',
  })
  const limit = 10

  const load = useCallback(async (off = 0) => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getCandidates({ ...filters, limit, offset: off })
      setCandidates(data.items)
      setTotal(data.total)
      setOffset(off)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { load(0) }, [load])

  function handleFilter(key, val) {
    setFilters(f => ({ ...f, [key]: val }))
  }

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="layout">
      <Topbar />
      <div className="page-content">
        <div className="page-header">
          <h1 className="page-title">Candidates</h1>
          <span style={{ color: 'var(--muted)', fontSize: 13 }}>
            {total} total
          </span>
        </div>

        {/* Filters */}
        <div className="filter-row">
          <input
            className="input"
            placeholder="Search by name, email, role…"
            value={filters.keyword}
            onChange={e => handleFilter('keyword', e.target.value)}
          />
          <select className="input" value={filters.status} onChange={e => handleFilter('status', e.target.value)}>
            <option value="">All statuses</option>
            {STATUS_OPTIONS.filter(Boolean).map(s => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <select className="input" value={filters.role_applied} onChange={e => handleFilter('role_applied', e.target.value)}>
            <option value="">All roles</option>
            {ROLE_OPTIONS.filter(Boolean).map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <input
            className="input"
            placeholder="Filter by skill…"
            value={filters.skill}
            onChange={e => handleFilter('skill', e.target.value)}
          />
        </div>

        {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <div className="spinner" style={{ width: 28, height: 28 }} />
          </div>
        ) : candidates.length === 0 ? (
          <div className="empty-state">
            <h3>No candidates found</h3>
            <p>Try adjusting your filters</p>
          </div>
        ) : (
          <>
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="candidate-table">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>Role Applied</th>
                    <th>Skills</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map(c => (
                    <tr key={c.id}>
                      <td>
                        <Link to={`/candidates/${c.id}`} className="candidate-link">{c.name}</Link>
                        <div className="candidate-email">{c.email}</div>
                      </td>
                      <td style={{ color: 'var(--muted)', fontSize: 13 }}>{c.role_applied}</td>
                      <td>
                        {c.skills.slice(0, 3).map(s => (
                          <span key={s} className="skill-tag">{s}</span>
                        ))}
                        {c.skills.length > 3 && <span className="skill-tag">+{c.skills.length - 3}</span>}
                      </td>
                      <td>
                        <span className={`status-badge status-${c.status}`}>{c.status}</span>
                      </td>
                      <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                        {new Date(c.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <span>Page {currentPage} of {totalPages || 1} ({total} candidates)</span>
              <div className="pagination-btns">
                <button
                  className="btn btn-sm"
                  disabled={offset === 0}
                  onClick={() => load(Math.max(0, offset - limit))}
                >← Prev</button>
                <button
                  className="btn btn-sm"
                  disabled={offset + limit >= total}
                  onClick={() => load(offset + limit)}
                >Next →</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}