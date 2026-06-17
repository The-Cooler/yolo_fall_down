export const DEFAULT_CLIENT_ID = 'e5cd7e4891bf95d1d19206ce24a7b32e'
export const DEFAULT_GATEWAY_BASE_URL = 'http://127.0.0.1:9500'
export const DEFAULT_ENCRYPT_HEADER_NAME = 'encrypt-key'
export const DEFAULT_RSA_PUBLIC_KEY = 'MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAKoR8mX0rGKLqzcWmOzbfj64K8ZIgOdHnzkXSOVOZbFu/TJhZ7rFAN+eaGkl3C4buccQd/EjEsj9ir7ijT7h96MCAwEAAQ=='
export const DEFAULT_RSA_PRIVATE_KEY = 'MIIBVAIBADANBgkqhkiG9w0BAQEFAASCAT4wggE6AgEAAkEAmc3CuPiGL/LcIIm7zryCEIbl1SPzBkr75E2VMtxegyZ1lYRD+7TZGAPkvIsBcaMs6Nsy0L78n2qh+lIZMpLH8wIDAQABAkEAk82Mhz0tlv6IVCyIcw/s3f0E+WLmtPFyR9/WtV3Y5aaejUkU60JpX4m5xNR2VaqOLTZAYjW8Wy0aXr3zYIhhQQIhAMfqR9oFdYw1J9SsNc+CrhugAvKTi0+BF6VoL6psWhvbAiEAxPPNTmrkmrXwdm/pQQu3UOQmc2vCZ5tiKpW10CgJi8kCIFGkL6utxw93Ncj4exE/gPLvKcT+1Emnoox+O9kRXss5AiAMtYLJDaLEzPrAWcZeeSgSIzbL+ecokmFKSDDcRske6QIgSMkHedwND1olF8vlKsJUGK3BcdtM8w4Xq7BpSBwsloE='

const TOKEN_KEYS = [
  'Authorization',
  'authorization',
  'Admin-Token',
  'AdminToken',
  'access_token',
  'accessToken',
  'token',
  'satoken',
  'satoken-token',
  'vue_admin_template_token',
]

const CLIENT_ID_KEYS = ['clientid', 'clientId', 'ClientId', 'CLIENT_ID']

export function resolveAuthConfig() {
  return {
    token: findAuthValue(TOKEN_KEYS),
    clientid: findRawValue(CLIENT_ID_KEYS) || DEFAULT_CLIENT_ID,
  }
}

export function normalizeBearerToken(token) {
  const value = normalizeTokenValue(token)
  if (!value) return ''
  return value.startsWith('Bearer ') ? value : `Bearer ${value}`
}

function findAuthValue(keys) {
  for (const raw of collectCandidateValues(keys)) {
    const token = normalizeTokenValue(raw)
    if (token) return token
  }
  return ''
}

function findRawValue(keys) {
  for (const raw of collectCandidateValues(keys)) {
    const value = normalizeRawString(raw)
    if (value) return value
  }
  return ''
}

function collectCandidateValues(keys) {
  return [
    ...collectStorageValues(window.localStorage, keys),
    ...collectStorageValues(window.sessionStorage, keys),
    ...collectCookieValues(keys),
  ]
}

function collectStorageValues(storage, keys) {
  if (!storage) return []
  const values = []
  for (const key of keys) {
    const value = storage.getItem(key)
    if (value) values.push(value)
  }

  const wanted = new Set(keys.map((key) => key.toLowerCase()))
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index)
    if (key && wanted.has(key.toLowerCase())) {
      const value = storage.getItem(key)
      if (value) values.push(value)
    }
  }
  return values
}

function collectCookieValues(keys) {
  const cookies = document.cookie
    .split(';')
    .map((item) => item.trim())
    .filter(Boolean)

  const values = []
  const wanted = new Set(keys.map((key) => key.toLowerCase()))
  for (const cookie of cookies) {
    const separator = cookie.indexOf('=')
    if (separator < 0) continue
    const key = decodeURIComponent(cookie.slice(0, separator))
    if (!wanted.has(key.toLowerCase())) continue
    values.push(decodeURIComponent(cookie.slice(separator + 1)))
  }
  return values
}

function normalizeTokenValue(raw) {
  const value = normalizeRawString(raw)
  if (!value) return ''

  const parsed = tryParseJson(value)
  if (typeof parsed === 'string') return normalizeTokenValue(parsed)
  if (parsed && typeof parsed === 'object') {
    for (const key of TOKEN_KEYS) {
      if (parsed[key]) return normalizeTokenValue(parsed[key])
    }
    if (parsed.data) return normalizeTokenValue(parsed.data)
    if (parsed.tokenInfo) return normalizeTokenValue(parsed.tokenInfo)
    if (parsed.user) return normalizeTokenValue(parsed.user)
  }

  return value.replace(/^Bearer\s+/i, '')
}

function normalizeRawString(raw) {
  if (raw == null) return ''
  const value = String(raw).trim()
  if (!value || value === 'undefined' || value === 'null') return ''
  return value
}

function tryParseJson(value) {
  if (!value.startsWith('{') && !value.startsWith('[') && !value.startsWith('"')) return null
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}
