import axios from 'axios'

type ApiResponse<T> = T

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const checkHealth = async () => {
  const res = await api.get('/health')
  return res.data
}

export const getStatus = async () => {
  const res = await api.get('/status')
  return res.data
}

export const processFolder = async (folder_path: string) => {
  const res = await api.post('/process/folder', { folder_path })
  return res.data
}

export const processUpload = async (formData: FormData) => {
  const res = await axios.post('/api/process/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

  return res.data
}

export const getReviewQueue = async () => {
  const res = await api.get('/review/queue')
  return res.data
}

export const submitReviewDecision = async (payload: {
  document_name: string
  human_decision: string
  reviewer_notes: string
}) => {
  const res = await api.post('/review/decision', payload)
  return res.data
}

export const getAuditLogs = async (limit: number = 50) => {
  const res = await api.get(`/audit/logs?limit=${limit}`)
  return res.data
}

export const resetSystem = async () => {
  const res = await api.post('/system/reset')
  return res.data
}

export const shutdownSystem = async () => {
  const res = await api.post('/system/shutdown')
  return res.data
}
