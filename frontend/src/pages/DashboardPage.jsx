import { useState, useEffect, useRef } from 'react'
import { getDashboardStats, getDashboardCharts, uploadCVs } from '../services/api'

export default function DashboardPage() {
  const [stats, setStats] = useState({})
  const [charts, setCharts] = useState({})
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const fileRef = useRef()

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      const [statsRes, chartsRes] = await Promise.all([
        getDashboardStats(),
        getDashboardCharts(),
      ])
      setStats(statsRes.data || {})
      setCharts(chartsRes.data || {})
    } catch (err) {
      console.error('Dashboard load error:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleFileUpload(e) {
    const files = Array.from(e.target.files).filter((file) => file.name.toLowerCase().endsWith('.pdf'))
    if (!files.length) return
    setUploading(true); setUploadResult(null)
    try {
      const res = await uploadCVs(files)
      setUploadResult(res)
    } catch (err) {
      console.error('Upload error:', err)
    } finally {
      setUploading(false)
    }
  }

  const scoreData = charts.score_distribution || {}

  if (loading) return <div className="loading"><div className="spinner" /></div>

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Intelligence Hub</h1>
          <p className="page-subtitle">Automated processing for active recruitment pipelines.</p>
        </div>
      </div>

      {/* Top section: Upload widget */}
      <div style={{ marginBottom: 22 }}>
        <div className="card">
          <div className="upload-widget">
            <div className="upload-icon-wrap">☁</div>
            <h3>CV Folder Upload</h3>
            <p>Select a local folder of PDFs to upload for processing.</p>
            <div className="upload-actions">
              <input
                type="file"
                ref={fileRef}
                multiple
                accept=".pdf"
                webkitdirectory="true"
                directory="true"
                style={{ display: 'none' }}
                onChange={handleFileUpload}
              />
              <button className="btn btn-primary" onClick={() => fileRef.current.click()} disabled={uploading}>
                {uploading ? '⏳ Uploading...' : '📂 Browse Folder'}
              </button>
            </div>
            {uploadResult && (
              <div className="alert alert-success" style={{ marginTop: 12, textAlign: 'left', width: '100%' }}>
                <span>✓</span>
                <div>
                  <div className="alert-title">Upload Complete</div>
                  <div style={{ fontSize: '0.8rem' }}>{uploadResult.data?.count || 0} file(s) uploaded</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Candidate Score Avg</div>
          <div className="stat-value">{stats.candidate_score_avg || '0.0'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Pipeline</div>
          <div className="stat-value">{stats.active_pipeline || 0}</div>
          <div className="stat-sub">Candidates</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Jobs</div>
          <div className="stat-value">{stats.active_jobs || 0}</div>
          <div className="stat-sub">Open positions</div>
        </div>
      </div>

      {/* Bottom: Score Chart */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
          <div>
            <div className="card-title">Score Distribution</div>
            <div className="card-subtitle">Candidates by score range</div>
          </div>
        </div>
        {Object.entries(scoreData).map(([range, count]) => (
          <div key={range} className="pub-row">
            <span className="pub-label">{range}</span>
            <div style={{ flex: 1 }}>
              <div className="progress-bar">
                <div className={`progress-fill ${range.startsWith('80') ? 'green' : range.startsWith('60') ? 'blue' : 'yellow'}`}
                  style={{ width: `${Math.min(100, count * 20)}%` }} />
              </div>
            </div>
            <span className="pub-count">{count} candidates</span>
          </div>
        ))}
      </div>
    </div>
  )
}
