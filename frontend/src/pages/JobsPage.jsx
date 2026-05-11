import { useState, useEffect } from 'react'
import { getJobs, createJob, smartMatch, getJob, updateJob, deleteJob } from '../services/api'

export default function JobsPage() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [editingJob, setEditingJob] = useState(null)
  const [selectedJob, setSelectedJob] = useState(null)
  const [matchResults, setMatchResults] = useState(null)
  const [matching, setMatching] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => { loadJobs() }, [])

  async function loadJobs() {
    try {
      const res = await getJobs()
      setJobs(res.data || [])
    } catch (err) {
      console.error('Jobs load error:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleRunMatch(jobId) {
    setMatching(true)
    setMatchResults(null)
    try {
      const res = await smartMatch(jobId)
      setMatchResults(res.data)
    } catch (err) {
      console.error('Smart match error:', err)
    } finally {
      setMatching(false)
    }
  }

  async function handleViewJob(jobId) {
    try {
      const res = await getJob(jobId)
      setSelectedJob(res.data)
    } catch (err) {
      console.error('View job error:', err)
    }
  }

  async function handleDeleteJob(job) {
    const ok = window.confirm(`Delete the job "${job.title}"? This cannot be undone.`)
    if (!ok) return
    setDeletingId(job.id)
    try {
      await deleteJob(job.id)
      await loadJobs()
      if (selectedJob?.id === job.id) {
        setSelectedJob(null)
      }
    } catch (err) {
      console.error('Delete job error:', err)
      window.alert('Failed to delete job. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) return <div className="loading"><div className="spinner" /></div>

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Job Postings</h1>
          <p className="page-subtitle">Manage positions and run Smart Match</p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
          + Create Job
        </button>
      </div>

      {/* Stats */}
      <div className="stats-row" style={{ marginBottom: 20 }}>
        <div className="stat-card">
          <div className="stat-label">Total Jobs</div>
          <div className="stat-value">{jobs.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active</div>
          <div className="stat-value">{jobs.filter(j => j.status === 'active').length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Applicants</div>
          <div className="stat-value">{jobs.reduce((s, j) => s + (j.total_applicants || 0), 0)}</div>
        </div>
      </div>

      {/* Job Cards */}
      {jobs.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No Jobs Yet</h3>
            <p>Create a job posting to start matching candidates.</p>
            <button className="btn btn-primary" style={{ marginTop: 14 }} onClick={() => setShowCreate(true)}>
              + Create First Job
            </button>
          </div>
        </div>
      ) : (
        <div className="jobs-grid">
          {jobs.map(j => (
            <div key={j.id} className="card job-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  <div className="card-title">{j.title}</div>
                  <div className="card-subtitle">{j.department || '—'} • {j.location || 'Remote'}</div>
                </div>
                <span className={`tier-badge ${j.status === 'active' ? 'excellent' : 'fair'}`}>
                  {j.status}
                </span>
              </div>

              {j.description && (
                <p style={{ fontSize: '0.82rem', color: 'var(--clr-text-secondary)', marginBottom: 12, lineHeight: 1.5 }}>
                  {j.description.slice(0, 120)}{j.description.length > 120 ? '...' : ''}
                </p>
              )}

              {j.required_skills?.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 12 }}>
                  {j.required_skills.slice(0, 5).map((s, i) => (
                    <span key={i} className="severity useful">{s}</span>
                  ))}
                </div>
              )}

              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary btn-sm" onClick={() => handleRunMatch(j.id)} disabled={matching}>
                  {matching ? '⏳ Matching...' : '⚡ Smart Match'}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => handleViewJob(j.id)}>
                  View Details
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => setEditingJob(j)}>
                  Edit
                </button>
                <button className="btn btn-danger btn-sm" onClick={() => handleDeleteJob(j)} disabled={deletingId === j.id}>
                  {deletingId === j.id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Smart Match Results */}
      {matchResults && (
        <div className="card" style={{ marginTop: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <div className="card-title">Smart Match Results</div>
              <div className="card-subtitle">{matchResults.total} candidates ranked by alignment</div>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={() => setMatchResults(null)}>✕ Close</button>
          </div>
          <div className="table-wrap" style={{ border: 'none' }}>
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Candidate</th>
                  <th>Alignment Score</th>
                  <th>Overall Score</th>
                </tr>
              </thead>
              <tbody>
                {(matchResults.candidates || []).slice(0, 15).map(c => (
                  <tr key={c.candidate_id} style={{ cursor: 'default' }}>
                    <td>
                      <span className={`rank-badge ${c.rank <= 3 ? 'top' : ''}`}>
                        {c.rank <= 3 ? ['🥇','🥈','🥉'][c.rank-1] : `#${c.rank}`}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{c.full_name || 'N/A'}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-bar" style={{ width: 80 }}>
                          <div className={`progress-fill ${c.alignment_score >= 70 ? 'green' : c.alignment_score >= 50 ? 'blue' : 'yellow'}`}
                            style={{ width: `${c.alignment_score}%` }} />
                        </div>
                        <span style={{ fontSize: '0.82rem' }}>{c.alignment_score?.toFixed(1)}</span>
                      </div>
                    </td>
                    <td>{(c.overall_score || 0).toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Job Detail Modal */}
      {selectedJob && (
        <div className="modal-overlay" onClick={() => setSelectedJob(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 700 }}>
            <div className="modal-header">
              <h3 className="modal-title">{selectedJob.title}</h3>
              <button className="modal-close" onClick={() => setSelectedJob(null)}>×</button>
            </div>
            <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
              <div className="detail-item" style={{ flex: 1 }}>
                <span className="detail-label">Department</span>
                <span className="detail-value">{selectedJob.department || '—'}</span>
              </div>
              <div className="detail-item" style={{ flex: 1 }}>
                <span className="detail-label">Location</span>
                <span className="detail-value">{selectedJob.location || 'Remote'}</span>
              </div>
              <div className="detail-item" style={{ flex: 1 }}>
                <span className="detail-label">Type</span>
                <span className="detail-value">{selectedJob.employment_type || '—'}</span>
              </div>
            </div>
            {selectedJob.description && (
              <div style={{ marginBottom: 16 }}>
                <div className="card-title" style={{ marginBottom: 4 }}>Description</div>
                <p style={{ fontSize: '0.82rem', color: 'var(--clr-text-secondary)', lineHeight: 1.7 }}>
                  {selectedJob.description}
                </p>
              </div>
            )}
            {selectedJob.candidates?.length > 0 && (
              <div>
                <div className="card-title" style={{ marginBottom: 8 }}>Matched Candidates ({selectedJob.candidates.length})</div>
                {selectedJob.candidates.map(c => (
                  <div key={c.candidate_id} className="detail-item">
                    <span style={{ fontWeight: 600 }}>{c.full_name}</span>
                    <span className={`score-badge ${c.alignment_score >= 70 ? 'excellent' : 'good'}`}>
                      {c.alignment_score?.toFixed(1)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={() => { setSelectedJob(null); setEditingJob(selectedJob) }}>
                Edit Job
              </button>
              <button className="btn btn-danger" onClick={() => handleDeleteJob(selectedJob)} disabled={deletingId === selectedJob.id}>
                {deletingId === selectedJob.id ? 'Deleting...' : 'Delete Job'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Job Modal */}
      {showCreate && <CreateJobModal onClose={() => setShowCreate(false)} onCreated={loadJobs} />}
      {editingJob && (
        <EditJobModal
          job={editingJob}
          onClose={() => setEditingJob(null)}
          onSaved={async () => {
            await loadJobs()
            setEditingJob(null)
          }}
        />
      )}
    </div>
  )
}

function CreateJobModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    title: '', department: '', location: '', employment_type: 'full_time',
    description: '', skills: '',
  })
  const [saving, setSaving] = useState(false)

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await createJob({
        title: form.title,
        department: form.department,
        location: form.location,
        employment_type: form.employment_type,
        description: form.description,
        required_skills: form.skills.split(',').map(s => s.trim()).filter(Boolean),
      })
      await onCreated()
      onClose()
    } catch (err) {
      console.error('Create job error:', err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Create New Job</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSave}>
          <div className="form-group">
            <label>Job Title *</label>
            <input type="text" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label>Department</label>
              <input type="text" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Location</label>
              <input type="text" value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} />
            </div>
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
              style={{
                width: '100%', minHeight: 80, background: 'var(--clr-surface2)', border: '1px solid var(--clr-border)',
                borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--clr-text)',
                fontFamily: 'var(--font)', fontSize: '0.82rem', resize: 'vertical',
              }}
            />
          </div>
          <div className="form-group">
            <label>Required Skills (comma-separated)</label>
            <input type="text" value={form.skills} onChange={e => setForm({ ...form, skills: e.target.value })}
              placeholder="Python, Machine Learning, Data Science" />
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving || !form.title}>
              {saving ? '⏳ Saving...' : '✓ Create Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EditJobModal({ job, onClose, onSaved }) {
  const [form, setForm] = useState({
    title: job.title || '',
    department: job.department || '',
    location: job.location || '',
    employment_type: job.employment_type || 'full_time',
    description: job.description || '',
    skills: (job.required_skills || []).join(', '),
    status: job.status || 'active',
  })
  const [saving, setSaving] = useState(false)

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await updateJob(job.id, {
        title: form.title,
        department: form.department || null,
        location: form.location || null,
        employment_type: form.employment_type || null,
        description: form.description || '',
        status: form.status || 'active',
        required_skills: form.skills.split(',').map(s => s.trim()).filter(Boolean),
      })
      await onSaved()
    } catch (err) {
      console.error('Update job error:', err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Edit Job</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSave}>
          <div className="form-group">
            <label>Job Title *</label>
            <input type="text" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label>Department</label>
              <input type="text" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Location</label>
              <input type="text" value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label>Employment Type</label>
              <select value={form.employment_type} onChange={e => setForm({ ...form, employment_type: e.target.value })}>
                <option value="full_time">Full Time</option>
                <option value="part_time">Part Time</option>
                <option value="contract">Contract</option>
                <option value="internship">Internship</option>
              </select>
            </div>
            <div className="form-group">
              <label>Status</label>
              <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="closed">Closed</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
              style={{
                width: '100%', minHeight: 80, background: 'var(--clr-surface2)', border: '1px solid var(--clr-border)',
                borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--clr-text)',
                fontFamily: 'var(--font)', fontSize: '0.82rem', resize: 'vertical',
              }}
            />
          </div>
          <div className="form-group">
            <label>Required Skills (comma-separated)</label>
            <input type="text" value={form.skills} onChange={e => setForm({ ...form, skills: e.target.value })}
              placeholder="Python, Machine Learning, Data Science" />
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving || !form.title}>
              {saving ? '⏳ Saving...' : '✓ Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
