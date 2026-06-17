import { trimSlash } from './fall'
import { decryptApiPayload, encryptApiPayload } from '../utils/crypto'

const TOKEN_FIELDS = ['access_token', 'accessToken', 'token', 'satoken', 'satoken-token']

export function createAuthApi(config) {
  return {
    getCaptcha: () => request(config, '/auth/code'),
    login: (payload) => login(config, payload),
    getInfo: () => request(config, '/system/user/getInfo', {
      headers: buildAuthHeaders(config),
    }),
  }
}

async function login(config, form) {
  const payload = {
    tenantId: form.tenantId || '000000',
    username: form.username,
    password: form.password,
    rememberMe: Boolean(form.rememberMe),
    code: form.code,
    uuid: form.uuid,
    clientId: config.clientid,
    grantType: 'password',
  }

  const headers = {
    'Content-Type': 'application/json',
    clientid: config.clientid,
  }
  let body = JSON.stringify(payload)

  if (config.loginEncrypted) {
    const encrypted = encryptApiPayload(payload, config.rsaPublicKey, config.encryptHeaderName)
    Object.assign(headers, encrypted.headers)
    body = encrypted.body
  }

  return request(config, '/auth/login', {
    method: 'POST',
    headers,
    body,
  })
}

async function request(config, path, options = {}) {
  const response = await fetch(`${trimSlash(config.gatewayBaseUrl)}${path}`, {
    ...options,
    headers: {
      clientid: config.clientid,
      ...(options.headers || {}),
    },
  })

  const payload = await parseResponse(response, config)
  if (!response.ok || payload.code !== 200) {
    throw new Error(normalizeError(payload) || '请求失败')
  }
  return payload.data ?? payload
}

async function parseResponse(response, config) {
  const text = await response.text()
  if (!text) return {}

  const encryptedKey = response.headers.get(config.encryptHeaderName || 'encrypt-key')
  if (encryptedKey && config.rsaPrivateKey) {
    const decryptedText = decryptApiPayload(text, encryptedKey, config.rsaPrivateKey)
    return parseJson(decryptedText)
  }
  if (encryptedKey && !config.rsaPrivateKey) {
    throw new Error('登录响应已加密，缺少响应 RSA 私钥')
  }
  return parseJson(text)
}

export function extractToken(payload) {
  const token = findToken(payload)
  return token ? String(token).replace(/^Bearer\s+/i, '') : ''
}

export function buildAuthHeaders(config) {
  const headers = {
    clientid: config.clientid,
  }
  if (config.token) {
    headers.Authorization = config.token.startsWith('Bearer ') ? config.token : `Bearer ${config.token}`
  }
  return headers
}

function findToken(value) {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    for (const item of value) {
      const token = findToken(item)
      if (token) return token
    }
    return ''
  }
  if (typeof value === 'object') {
    for (const field of TOKEN_FIELDS) {
      if (value[field]) return value[field]
    }
    return findToken(value.data) || findToken(value.tokenInfo) || findToken(value.user)
  }
  return ''
}

function parseJson(text) {
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
