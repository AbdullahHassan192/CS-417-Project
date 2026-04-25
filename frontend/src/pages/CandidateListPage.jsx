import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { getCandidateList } from '../services/api'

export default function CandidateListPage() {
  const [candidates, setCandidates] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [sortBy, setSortBy] = useState('overall_score')
  const [sortOrder, setSortOrder] = useState('desc')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => { loadCandidates() }, [page, sortBy, sortOrder])

  async function loadCandidates() {
    setLoading(true)
    try {
      const res = await getCandidateList({ page, pageSize, sortBy, sortOrder, search: search || undefined })
      const data = res.data || {}
      setCandidates(data.candidates || [])
      setTotal(data.total || 0)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  function handleSort(field) {
    if (sortBy === field) setSortOrder(o => o === 'desc' ? 'asc' : 'desc')
    else { setSortBy(field); setSortOrder('desc') }
  }

  function handleSearch(e) { e.preventDefault(); setPage(1); loadCandidates() }

  const totalPages = Math.ceil(total / pageSize)
  const si = (f) => sortBy === f ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''

  const allCandidates = candidates
  const shortlisted = allCandidates.filter(c => (c.overall_score || 0) >= 70).length
  const pending = allCandidates.filter(c => (c.missing_info_count || 0) > 0).length
  const avgExp = allCandidates.length
    ? (allCandidates.reduce((s, c) => s + (c.professional_strength || 0), 0) / allCandidates.length).toFixed(1)
    : '0.0'

  function initials(name) {
    if (!name) return '?'
    const parts = name.trim().split(' ')
    return parts.length >= 2 ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase() : name.slice(0, 2).toUpperCase()
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Candidate Pool</h1>
          <p className="page-subtitle">Review and manage {total} professional profiles</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary btn-sm">≡ Filter By ▾</button>
          <button className="btn btn-secondary btn-sm">↕ Sort: Recent ▾</button>
          <Link to="/processing" className="btn btn-primary btn-sm">+ Import Candidates</Link>
        </div>
      </div>

      {/* Stats */}
      <div className="cand-stats">
        <div className="cand-stat">
          <div className="label">Active Shortlist</div>
          <div className="val">{shortlisted}</div>
          <div className="sub"><span className="up">+11%</span> this week</div>
        </div>
        <div className="cand-stat">
          <div className="label">Pending Reviews</div>
          <div className="val">{pending}</div>
          <div className="sub">Requires action</div>
        </div>
        <div className="cand-stat">
          <div className="label">Total Candidates</div>
          <div className="val">{total}</div>
          <div className="sub">In pipeline</div>
        </div>
        <div className="cand-stat">
          <div className="label">Average Score</div>
          <div className="val">{avgExp}</div>
          <div className="sub">Overall strength</div>
        </div>
      </div>

      {/* Search */}
      <div className="filter-bar">
        <form onSubmit={handleSearch} className="input-group" style={{ flex: 1 }}>
          <input
            type="search"
            placeholder="Search by name..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary btn-sm">Search</button>
          {search && (
            <button type="button" className="btn btn-secondary btn-sm"
              onClick={() => { setSearch(''); setPage(1); setTimeout(loadCandidates, 0) }}>
              Clear
            </button>
          )}
        </form>
      </div>

      {/* Table */}
      {loading ? (
        <div className="loading"><div className="spinner" /></div>
      ) : candidates.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No Candidates Found</h3>
            <p>Process CVs to see candidates here.</p>
            <Link to="/processing" className="btn btn-primary" style={{ marginTop: 14 }}>Process CVs</Link>
          </div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('full_name')}>Candidate Name{si('full_name')}</th>
                <th onClick={() => handleSort('educational_strength')}>Highest Degree{si('educational_strength')}</th>
                <th onClick={() => handleSort('professional_strength')}>Experience (Yrs){si('professional_strength')}</th>
                <th onClick={() => handleSort('overall_score')}>Overall Score{si('overall_score')}</th>
                <th onClick={() => handleSort('publication_count')}>Publications{si('publication_count')}</th>
                <th onClick={() => handleSort('completeness_percentage')}>Status{si('completeness_percentage')}</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map(c => (
                <tr key={c.candidate_id} onClick={() => navigate(`/candidates/${c.candidate_id}`)}>
                  <td>
                    <div className="cand-cell">
                      <div className="cand-avatar">{initials(c.full_name)}</div>
                      <div>
                        <div className="cand-name">{c.full_name || 'N/A'}</div>
                        <div className="cand-email">{c.email || c.source_file || ''}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ fontSize: '0.8rem' }}>
                    {c.educational_strength >= 8 ? 'PhD' : c.educational_strength >= 6 ? 'MS / MSc' : c.educational_strength >= 4 ? 'BS / BSc' : 'Other'}
                  </td>
                  <td>{(c.professional_strength || 0).toFixed(1)}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className="progress-bar" style={{ width: 80 }}>
                        <div className={`progress-fill ${(c.overall_score || 0) >= 80 ? 'green' : (c.overall_score || 0) >= 60 ? 'blue' : 'yellow'}`}
                          style={{ width: `${c.overall_score || 0}%` }} />
                      </div>
                      <span style={{ fontSize: '0.78rem' }}>{(c.overall_score || 0).toFixed(1)}</span>
                    </div>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {c.publication_count || 0}
                  </td>
                  <td>
                    <span className={`tier-badge ${c.overall_tier || 'below_average'}`}>
                      {(c.missing_info_count || 0) === 0 ? '✓ Complete' : `${c.missing_info_count} missing`}
                    </span>
                  </td>
                  <td onClick={e => { e.stopPropagation(); navigate(`/candidates/${c.candidate_id}`) }}>
                    <button className="btn btn-secondary btn-sm">View →</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          <div className="pagination">
            <span className="pagination-info">
              Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total} Candidates
            </span>
            <div className="pagination-btns">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>‹</button>
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(n => (
                <button key={n} className={page === n ? 'active' : ''} onClick={() => setPage(n)}>{n}</button>
              ))}
              {totalPages > 5 && <button disabled>…</button>}
              {totalPages > 5 && <button onClick={() => setPage(totalPages)}>{totalPages}</button>}
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>›</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
