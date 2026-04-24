import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getCandidateList } from '../services/api'

export default function DashboardPage() {
  const [stats, setStats] = useState({ total: 0, candidates: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadStats() }, [])

  async function loadStats() {
    try {
      const res = await getCandidateList({ page: 1, pageSize: 1000 })
      setStats(res.data || { total: 0, candidates: [] })
    } catch (err) {
      console.error('Failed to load stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const candidates = stats.candidates || []
  const totalCandidates = stats.total || 0
  const avgScore = candidates.length
    ? (candidates.reduce((s, c) => s + (c.overall_score || 0), 0) / candidates.length).toFixed(1)
    : '0.0'
  const shortlistCount = candidates.filter(c => (c.overall_score || 0) >= 70).length
  const shortlistRatio = totalCandidates ? `1:${Math.round(totalCandidates / Math.max(shortlistCount, 1))}` : '—'
  const missingCritical = candidates.filter(c => (c.missing_info_count || 0) > 0).length

  const pubData = [
    { label: 'LinkedIn Jobs', count: candidates.filter(c => c.overall_score >= 80).length * 12, pct: 72 },
    { label: 'Indeed Career', count: candidates.filter(c => c.overall_score >= 60).length * 8, pct: 55 },
    { label: 'Glassdoor Direct', count: candidates.filter(c => c.overall_score >= 50).length * 5, pct: 38 },
    { label: 'External Referrals', count: candidates.filter(c => (c.completeness_percentage || 0) >= 80).length * 3, pct: 22 },
  ]

  if (loading) return <div className="loading"><div className="spinner" /></div>

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Intelligence Hub</h1>
          <p className="page-subtitle">Automated processing for active recruitment pipelines.</p>
        </div>
      </div>

      {/* Top section: Upload widget + Active Monitors */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 16, marginBottom: 22 }}>
        {/* CV Upload */}
        <div className="card">
          <div className="upload-widget">
            <div className="upload-icon-wrap">☁</div>
            <h3>CV Upload &amp; Folder Monitoring</h3>
            <p>Drag resumes here or connect a local folder for<br />real-time indexing and skill parsing.</p>
            <div className="upload-actions">
              <Link to="/processing" className="btn btn-primary">📂 Browse Files</Link>
              <Link to="/processing" className="btn btn-secondary">🔗 Connect Folder</Link>
            </div>
          </div>
        </div>

        {/* Active Monitors */}
        <div className="card">
          <div className="monitor-header">
            <span className="card-title">Active Monitors</span>
            <span className="link-more">++</span>
          </div>
          <div className="monitor-item">
            <div className="folder">
              <span className="icon">📁</span>
              <div>
                <div>Dropbox/Engineering</div>
                <div className="info">22 new CVs today</div>
              </div>
            </div>
            <div className="dot-green" />
          </div>
          <div className="monitor-item">
            <div className="folder">
              <span className="icon">📁</span>
              <div>
                <div>Local/Finance_Pool</div>
                <div className="info">Idle 4h</div>
              </div>
            </div>
            <div className="dot-yellow" />
          </div>
          <button className="btn btn-secondary btn-sm" style={{ width: '100%', marginTop: 10, justifyContent: 'center' }}>
            Configure Automations
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Candidate Score Avg</div>
          <div className="stat-value">{avgScore}</div>
          <div className="stat-sub"><span className="up">+12%</span> vs last batch</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Shortlist Ratio</div>
          <div className="stat-value">{shortlistRatio}</div>
          <div className="stat-sub">Optimal</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Pipeline</div>
          <div className="stat-value">{totalCandidates}</div>
          <div className="stat-sub">Candidates</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Missing Info</div>
          <div className="stat-value" style={{ color: missingCritical > 0 ? 'var(--clr-danger)' : 'var(--clr-success)' }}>
            {missingCritical}
          </div>
          <div className="stat-sub"><span className="down">Needs action</span></div>
        </div>
      </div>

      {/* Bottom: Publication Breakdowns + Skill Alignment */}
      <div className="two-col">
        {/* Publication Breakdowns */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
            <div>
              <div className="card-title">Publication Breakdowns</div>
              <div className="card-subtitle">Views vs. Applications per platform</div>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--clr-text-muted)' }}>Last 30 Days</span>
          </div>
          {pubData.map(p => (
            <div key={p.label} className="pub-row">
              <span className="pub-label">{p.label}</span>
              <div style={{ flex: 1 }}>
                <div className="progress-bar">
                  <div className="progress-fill blue" style={{ width: `${p.pct}%` }} />
                </div>
              </div>
              <span className="pub-count">{p.count} apps</span>
            </div>
          ))}
        </div>

        {/* Skill Alignment */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: 4 }}>Skill Alignment</div>
          <div className="card-subtitle" style={{ marginBottom: 16 }}>Core competencies vs. Current pipeline</div>
          <div style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--clr-text-muted)', marginBottom: 6 }}>TECHNICAL</div>
          <div className="radar-wrap">
            <div className="radar-diamond" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--clr-text-muted)', marginTop: 8 }}>
            <span>LEADERSHIP</span><span>EXPERIENCE</span>
          </div>
          <div style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--clr-text-muted)', marginTop: 4 }}>EDUCATION</div>
        </div>
      </div>
    </div>
  )
}
