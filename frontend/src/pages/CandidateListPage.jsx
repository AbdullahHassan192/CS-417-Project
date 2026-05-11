import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { getCandidateList, deleteCandidate, updateCandidateStatus } from '../services/api'

export default function CandidateListPage() {
  const [candidates, setCandidates] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [sortBy, setSortBy] = useState('overall_score')
  const [sortOrder, setSortOrder] = useState('desc')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [deletingId, setDeletingId] = useState(null)
  const [updatingId, setUpdatingId] = useState(null)
  const [shortlistCount, setShortlistCount] = useState(0)
  const [unreviewedCount, setUnreviewedCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => { loadCandidates() }, [page, sortBy, sortOrder, statusFilter])

  async function loadCandidates() {
    setLoading(true)
    try {
      const [listRes, shortlistRes, unreviewedRes] = await Promise.all([
        getCandidateList({
          page,
          pageSize,
          sortBy,
          sortOrder,
          search: search || undefined,
          status: statusFilter === 'all' ? undefined : statusFilter,
        }),
        getCandidateList({ page: 1, pageSize: 1, status: 'shortlisted' }),
        getCandidateList({ page: 1, pageSize: 1, status: 'unreviewed' }),
      ])

      const data = listRes.data || {}
      setCandidates(data.candidates || [])
      setTotal(data.total || 0)
      setShortlistCount(shortlistRes.data?.total || 0)
      setUnreviewedCount(unreviewedRes.data?.total || 0)
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

  async function handleStatusUpdate(candidateId, nextStatus) {
    setUpdatingId(candidateId)
    try {
      await updateCandidateStatus(candidateId, nextStatus)
      if (statusFilter !== 'all' && nextStatus !== statusFilter) {
        await loadCandidates()
      } else {
        setCandidates(prev => prev.map(c => c.candidate_id === candidateId ? { ...c, pipeline_status: nextStatus } : c))
      }
    } catch (err) {
      console.error('Failed to update status:', err)
      window.alert('Failed to update candidate status. Please try again.')
    } finally {
      setUpdatingId(null)
    }
  }

  async function handleDeleteCandidate(candidate) {
    const candidateName = candidate.full_name || candidate.candidate_id
    const ok = window.confirm(
      `Delete ${candidateName} and all related records? This cannot be undone.`
    )
    if (!ok) return

    setDeletingId(candidate.candidate_id)
    try {
      await deleteCandidate(candidate.candidate_id)
      if (candidates.length === 1 && page > 1) {
        setPage(page - 1)
      } else {
        await loadCandidates()
      }
    } catch (err) {
      console.error('Failed to delete candidate:', err)
      window.alert('Failed to delete candidate. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }

  const totalPages = Math.ceil(total / pageSize)
  const si = (f) => sortBy === f ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''

  const avgExp = candidates.length
    ? (candidates.reduce((s, c) => s + (c.professional_strength || 0), 0) / candidates.length).toFixed(1)
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
          <Link to="/processing" className="btn btn-primary btn-sm">+ Import Candidates</Link>
        </div>
      </div>

      {/* Stats */}
      <div className="cand-stats">
        <div className="cand-stat">
          <div className="label">Active Shortlist</div>
          <div className="val">{shortlistCount}</div>
          <div className="sub">Shortlisted</div>
        </div>
        <div className="cand-stat">
          <div className="label">Pending Reviews</div>
          <div className="val">{unreviewedCount}</div>
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

      {/* Search + Status Filter */}
      <div className="filter-bar">
        <div className="status-filter">
          {[
            { id: 'all', label: 'All' },
            { id: 'shortlisted', label: 'Shortlisted' },
            { id: 'rejected', label: 'Rejected' },
            { id: 'unreviewed', label: 'Unreviewed' },
          ].map(option => (
            <button
              key={option.id}
              type="button"
              className={`btn btn-sm ${statusFilter === option.id ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => { setStatusFilter(option.id); setPage(1) }}
            >
              {option.label}
            </button>
          ))}
        </div>
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
                <th>Pipeline</th>
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
                  <td>{((c.total_years_of_experience ?? c.professional_strength) || 0).toFixed(1)}</td>
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
                  <td>
                    <span className={`status-badge ${c.pipeline_status || 'unreviewed'}`}>
                      {(c.pipeline_status || 'unreviewed').replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => navigate(`/candidates/${c.candidate_id}`)}
                      >
                        View →
                      </button>
                      <button
                        className="btn btn-success btn-sm"
                        disabled={updatingId === c.candidate_id}
                        onClick={() => handleStatusUpdate(c.candidate_id, 'shortlisted')}
                      >
                        Shortlist
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        disabled={updatingId === c.candidate_id}
                        onClick={() => handleStatusUpdate(c.candidate_id, 'rejected')}
                      >
                        Reject
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        disabled={updatingId === c.candidate_id}
                        onClick={() => handleStatusUpdate(c.candidate_id, 'unreviewed')}
                      >
                        Clear
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        disabled={deletingId === c.candidate_id}
                        onClick={() => handleDeleteCandidate(c)}
                      >
                        {deletingId === c.candidate_id ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
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
              {totalPages > 5 && <span className="pagination-ellipsis">…</span>}
              {totalPages > 5 && <button onClick={() => setPage(totalPages)}>{totalPages}</button>}
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>›</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
