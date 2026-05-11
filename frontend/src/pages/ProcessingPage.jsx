import { useRef, useState } from 'react'
import { processFolder, uploadCVs } from '../services/api'

export default function ProcessingPage() {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [selectedFolder, setSelectedFolder] = useState('')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const fileRef = useRef(null)

  function handleFolderSelect(e) {
    const files = Array.from(e.target.files).filter((file) => file.name.toLowerCase().endsWith('.pdf'))
    if (!files.length) {
      setSelectedFiles([])
      setSelectedFolder('')
      setError('No PDF files found in the selected folder.')
      return
    }
    const firstPath = files[0].webkitRelativePath || files[0].name
    const folderName = firstPath.split('/')[0] || 'Selected Folder'
    setSelectedFiles(files)
    setSelectedFolder(folderName)
    setError(null)
  }

  async function handleProcess(e) {
    e.preventDefault()
    if (!selectedFiles.length) {
      setError('Select a folder with PDF CVs to continue.')
      return
    }
    setProcessing(true); setResult(null); setError(null)
    try {
      const uploadRes = await uploadCVs(selectedFiles)
      const uploadDir = uploadRes.data?.upload_dir
      if (!uploadDir) {
        setError('Upload completed, but no server folder was returned.')
        return
      }

      const res = await processFolder(uploadDir)
      if (res.status === 'success' || res.data?.status === 'completed') {
        setResult(res.data)
      } else {
        setError(res.error || res.data?.message || 'Processing failed. Please try again.')
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
          <p className="page-subtitle">Upload a folder of CVs to run analysis.</p>
        </div>
      </div>

      {/* Form */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title" style={{ marginBottom: 4 }}>CV Folder Upload</div>
        <div className="card-subtitle" style={{ marginBottom: 16 }}>
          Choose a local folder that contains PDF CVs.
        </div>
        <form onSubmit={handleProcess}>
          <div className="upload-widget" style={{ padding: '10px 0 0' }}>
            <input
              type="file"
              ref={fileRef}
              webkitdirectory="true"
              directory="true"
              multiple
              accept=".pdf"
              onChange={handleFolderSelect}
              style={{ display: 'none' }}
              disabled={processing}
            />
            <div className="upload-actions" style={{ justifyContent: 'center' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => fileRef.current?.click()}
                disabled={processing}
              >
                📂 Browse Folder
              </button>
              <button type="submit" className="btn btn-primary" disabled={processing || !selectedFiles.length}>
                {processing ? '⏳ Processing...' : '▶ Start Processing'}
              </button>
            </div>
          </div>
        </form>
        {selectedFolder && (
          <div style={{ marginTop: 10, fontSize: '0.78rem', color: 'var(--clr-text-muted)' }}>
            Selected folder: {selectedFolder} ({selectedFiles.length} PDF file(s))
          </div>
        )}
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

    </div>
  )
}
