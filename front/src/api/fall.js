import { normalizeBearerToken } from '../utils/auth'
import { authStore } from '../store/auth.js'
import router from '../router/index.js'

export function createFallApi(config) {
  async function request(path, options = {}) {
    config.token = authStore.token

    const headers = buildHeaders(config)
    Object.assign(headers, options.headers || {})
    if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'

    const response = await fetch(`${trimSlash(config.fallBaseUrl)}${path}`, {
      ...options,
      headers,
    })
    const payload = await parseJson(response)

    if (response.status === 401 || payload.code === 401) {
      authStore.clearToken()
      router.replace('/login')
      throw new Error(normalizeError(payload) || '登录已过期，请重新登录')
    }

    if (!response.ok || payload.code !== 200) {
      throw new Error(normalizeError(payload) || '请求失败')
    }
    return payload.data
  }

  return {
    listCameras: () => request('/cameras'),
    createCamera: (camera) => request('/cameras', {
      method: 'POST',
      body: JSON.stringify(camera),
    }),
    updateCamera: (cameraId, camera) => request(`/cameras/${cameraId}`, {
      method: 'PATCH',
      body: JSON.stringify(camera),
    }),
    getTask: (cameraId) => request(`/tasks/${cameraId}`),
    setDetection: (cameraId, payload) => request(`/tasks/${cameraId}/detection`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
    setBoxes: (cameraId, enabled) => request(`/tasks/${cameraId}/boxes`, {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),
    listAlerts: (cameraId, limit = 30) => request(
      `/alerts?camera_id=${encodeURIComponent(cameraId)}&limit=${limit}`,
    ),
    markAlertRead: (alertId) => request(`/alerts/${alertId}/read`, { method: 'POST' }),
    deleteAlert: (alertId) => request(`/alerts/${alertId}`, { method: 'DELETE' }),
    updateTaskParams: (cameraId, params) => request(`/tasks/${cameraId}/params`, {
      method: 'PUT',
      body: JSON.stringify(params),
    }),
  }
}

export function buildHeaders(config) {
  const headers = {
    project_id: config.projectId,
    clientid: config.clientid,
  }
  if (config.token) {
    headers.Authorization = normalizeBearerToken(config.token)
  }
  return headers
}

export function trimSlash(value) {
  return String(value || '').replace(/\/$/, '')
}

async function parseJson(response) {
  const text = await response.text()
  if (!text) return {}
  try {
    return JSON.parse(text)
  } catch {
    return { msg: text }
  }
}

function normalizeError(payload) {
  if (!payload) return ''
  if (typeof payload.detail === 'string') return payload.detail
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join('；')
  }
  return payload.msg || payload.message || ''
}
