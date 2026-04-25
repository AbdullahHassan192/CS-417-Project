import { useState } from 'react'
import { processFolder } from '../services/api'

export default function ProcessingPage() {
  const [folderPath, setFolderPath] = useState('')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleProcess(e) {
    e.preventDefault()
    if (!folderPath.trim()) return
    setProcessing(true); setResult(null); setError(null)
    try {
      const res = await processFolder(folderPath.trim())
      if (res.status === 'success' || res.data?.status === 'completed') {
        setResult(res.data)
      } else {
        setError(res.error || res.data?.message || 'Processing failed. Check the folder path and try again.')
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to process CVs.')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Process CVs</h1>
          <p className="page-subtitle">Run M1 preprocessing and M2 analysis on CV folders</p>
        </div>
      </div>

      {/* Form */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title" style={{ marginBottom: 4 }}>CV Folder Path</div>
        <div className="card-subtitle" style={{ marginBottom: 16 }}>
          Provide the path to a folder containing PDF CVs, or a single PDF file.
        </div>
        <form onSubmit={handleProcess} className="input-group">
          <input
            type="text"
            placeholder="e.g., C:\Users\...\All_CVs"
            value={folderPath}
            onChange={e => setFolderPath(e.target.value)}
            style={{ flex: 1 }}
            disabled={processing}
          />
          <button type="submit" className="btn btn-primary" disabled={processing || !folderPath.trim()}>
            {processing ? '⏳ Processing...' : '▶ Start Processing'}
          </button>
        </form>
      </div>

      {/* Spinner */}
      {processing && (
        <div className="card" style={{ textAlign: 'center', padding: 40, marginBottom: 16 }}>
          <div className="spinner" style={{ margin: '0 auto 16px' }} />
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Processing CVs…</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--clr-text-muted)' }}>
            This may take a few minutes depending on the number of CVs and API response times.
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: '1.1rem' }}>✗</span>
          <div>
            <div className="alert-title">Processing Error</div>
            <div>{error}</div>
          </div>
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="alert alert-success" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: '1.1rem' }}>✓</span>
          <div>
            <div className="alert-title">Processing Complete</div>
            <div style={{ fontSize: '0.8rem', marginTop: 4 }}>
              {result.message} &nbsp;|&nbsp; Files: {result.file_count || 0} &nbsp;|&nbsp; Job: {result.job_id}
            </div>
          </div>
        </div>
      )}

      {/* How It Works */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: 16 }}>How It Works</div>
        <div className="timeline">
          <div className="timeline-item">
            <div className="timeline-title">Step 1: M1 Preprocessing</div>
            <div className="timeline-subtitle">PDF CVs are read using PyMuPDF and sent to Gemini LLM for structured extraction.</div>
          </div>
          <div className="timeline-item">
            <div className="timeline-title">Step 2: CSV Generation</div>
            <div className="timeline-subtitle">Extracted data is normalized and saved to 6 relational CSV files (candidates, education, experience, publications, books, patents).</div>
          </div>
          <div className="timeline-item">
            <div className="timeline-title">Step 3: M2 Analysis</div>
            <div className="timeline-subtitle">Educational and employment profiles are analyzed, missing info detected, and overall scores calculated.</div>
          </div>
          <div className="timeline-item">
            <div className="timeline-title">Step 4: Results Ready</div>
            <div className="timeline-subtitle">Assessment results are saved as JSON files and served via the web interface.</div>
          </div>
        </div>
      </div>
    </div>
  )
}
