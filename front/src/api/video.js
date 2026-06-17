import { trimSlash } from './fall'

export function buildMjpegUrl(config, camera) {
  if (!camera) return ''
  const url = new URL(`${trimSlash(config.videoBaseUrl)}/streams/mjpeg`)
  url.searchParams.set('project_id', config.projectId)
  url.searchParams.set('source_url', normalizeStreamUrl(camera.source_url))
  if (camera.suffix) url.searchParams.set('suffix', camera.suffix)
  if (camera.auto_append_suffix === false) url.searchParams.set('auto_append_suffix', 'false')
  if (config.videoReloadKey) url.searchParams.set('_t', config.videoReloadKey)
  return url.toString()
}

export async function probeVideoStream(config, camera) {
  const response = await fetch(`${trimSlash(config.videoBaseUrl)}/streams/probe`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      project_id: config.projectId,
    },
    body: JSON.stringify({
      source_url: normalizeStreamUrl(camera.source_url),
      suffix: camera.suffix || null,
      auto_append_suffix: camera.auto_append_suffix !== false,
      timeout_ms: 5000,
    }),
  })
  const payload = await parseJson(response)
  if (!response.ok || payload.code !== 200) {
    throw new Error(normalizeError(payload) || '视频探测失败')
  }
  return payload.data
}

export function normalizeStreamUrl(value) {
  const raw = String(value || '').trim()
  const duplicatedProtocol = raw.match(/^(rtsp|rtmp|http|https|file)\s+((?:rtsp|rtmp|http|https|file):\/\/.+)$/i)
  if (duplicatedProtocol) return duplicatedProtocol[2].trim()
  return raw.replace(/\s+/g, ' ')
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
