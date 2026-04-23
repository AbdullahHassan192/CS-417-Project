import axios from 'axios'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// ── Candidate endpoints ─────────────────────────────────────

export async function processFolder(folderPath) {
  const res = await api.post('/candidates/process-folder', { folder_path: folderPath })
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
} = {}) {
  const params = { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder }
  if (search) params.search = search
  if (minScore !== null) params.min_score = minScore
  if (maxScore !== null) params.max_score = maxScore
  const res = await api.get('/candidates/list', { params })
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

export default api
