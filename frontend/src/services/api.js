import axios from 'axios'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// ── JWT interceptor ─────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('talash_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('talash_token')
      localStorage.removeItem('talash_user')
      // Don't redirect here; let the app handle it
    }
    return Promise.reject(err)
  }
)

// ── Auth ─────────────────────────────────────────────────────
export async function login(email, password) {
  const res = await api.post('/auth/login', { email, password })
  return res.data
}

export async function logout() {
  localStorage.removeItem('talash_token')
  localStorage.removeItem('talash_user')
  return { status: 'success' }
}

export async function getMe() {
  const res = await api.get('/auth/me')
  return res.data
}

// ── Candidate endpoints ─────────────────────────────────────
export async function processFolder(folderPath) {
  const res = await api.post('/candidates/process-folder', { folder_path: folderPath })
  return res.data
}

export async function uploadCVs(files) {
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))
  const res = await api.post('/candidates/upload-cv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function getCandidateList({
  page = 1,
  pageSize = 10,
  sortBy = 'overall_score',
  sortOrder = 'desc',
  search = '',
  minScore = null,
  maxScore = null,
  status = null,
} = {}) {
  const params = { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder }
  if (search) params.search = search
  if (minScore !== null) params.min_score = minScore
  if (maxScore !== null) params.max_score = maxScore
  if (status) params.status = status
  const res = await api.get('/candidates/list', { params })
  return res.data
}

export async function updateCandidateStatus(candidateId, status) {
  const res = await api.post(`/candidates/${candidateId}/status`, { status })
  return res.data
}

export async function getFullAssessment(candidateId) {
  const res = await api.get(`/candidates/${candidateId}/full-assessment`)
  return res.data
}

export async function getMissingInfo(candidateId) {
  const res = await api.get(`/candidates/${candidateId}/missing-info`)
  return res.data
}

export async function sendInfoRequest(candidateId, emailData = {}) {
  const res = await api.post(`/candidates/${candidateId}/send-info-request`, emailData)
  return res.data
}

export async function batchProcess(candidateIds = []) {
  const res = await api.post('/candidates/batch-process', { candidate_ids: candidateIds })
  return res.data
}

export async function getCandidateSummary(candidateId) {
  const res = await api.get(`/candidates/${candidateId}/summary`)
  return res.data
}

export async function deleteCandidate(candidateId) {
  const res = await api.delete(`/candidates/${candidateId}`)
  return res.data
}

// ── Dashboard / Analytics ────────────────────────────────────
export async function getDashboardStats() {
  const res = await api.get('/dashboard/stats')
  return res.data
}

export async function getDashboardCharts() {
  const res = await api.get('/dashboard/charts')
  return res.data
}

export async function getAnalyticsCandidates() {
  const res = await api.get('/analytics/candidates')
  return res.data
}

export async function getEducationAnalytics() {
  const res = await api.get('/analytics/education')
  return res.data
}

export async function getPublicationAnalytics() {
  const res = await api.get('/analytics/publications')
  return res.data
}

export async function getRankings() {
  const res = await api.get('/rankings')
  return res.data
}

// ── Jobs ─────────────────────────────────────────────────────
export async function getJobs() {
  const res = await api.get('/jobs')
  return res.data
}

export async function createJob(data) {
  const res = await api.post('/jobs', data)
  return res.data
}

export async function getJob(jobId) {
  const res = await api.get(`/jobs/${jobId}`)
  return res.data
}

export async function updateJob(jobId, data) {
  const res = await api.patch(`/jobs/${jobId}`, data)
  return res.data
}

export async function deleteJob(jobId) {
  const res = await api.delete(`/jobs/${jobId}`)
  return res.data
}

export async function smartMatch(jobId) {
  const res = await api.post(`/jobs/${jobId}/match`)
  return res.data
}

export default api
