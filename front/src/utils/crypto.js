import CryptoJS from 'crypto-js'
import JSEncrypt from 'jsencrypt'

const KEY_LINE_LENGTH = 64
const AES_KEY_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

export function encryptApiPayload(data, publicKey, headerName = 'encrypt-key') {
  const rsaPublicKey = normalizePublicKey(publicKey)
  if (!rsaPublicKey) throw new Error('缺少请求 RSA 公钥')

  const aesKey = generateAesKey()
  const encryptedKey = rsaEncrypt(encodeBase64(aesKey), rsaPublicKey)
  const json = typeof data === 'string' ? data : JSON.stringify(data)

  return {
    body: encryptWithAes(json, aesKey),
    headers: {
      [headerName]: encryptedKey,
    },
  }
}

export function decryptApiPayload(data, encryptedKey, privateKey) {
  const rsaPrivateKey = normalizePrivateKey(privateKey)
  if (!rsaPrivateKey) throw new Error('缺少响应 RSA 私钥')

  const base64AesKey = rsaDecrypt(encryptedKey, rsaPrivateKey)
  const aesKey = decodeBase64(base64AesKey)
  return decryptWithAes(data, aesKey)
}

function generateAesKey() {
  let key = ''
  const values = new Uint32Array(32)
  window.crypto.getRandomValues(values)
  for (const value of values) {
    key += AES_KEY_CHARS[value % AES_KEY_CHARS.length]
  }
  return key
}

function encodeBase64(value) {
  return btoa(value)
}

function decodeBase64(value) {
  return atob(value)
}

function encryptWithAes(data, key) {
  return CryptoJS.AES.encrypt(data, CryptoJS.enc.Utf8.parse(key), {
    mode: CryptoJS.mode.ECB,
    padding: CryptoJS.pad.Pkcs7,
  }).toString()
}

function decryptWithAes(data, key) {
  const decrypted = CryptoJS.AES.decrypt(data, CryptoJS.enc.Utf8.parse(key), {
    mode: CryptoJS.mode.ECB,
    padding: CryptoJS.pad.Pkcs7,
  })
  const text = decrypted.toString(CryptoJS.enc.Utf8)
  if (!text) throw new Error('响应数据解密失败')
  return text
}

function rsaEncrypt(data, publicKey) {
  const encrypt = new JSEncrypt()
  encrypt.setPublicKey(publicKey)
  const encrypted = encrypt.encrypt(data)
  if (!encrypted) throw new Error('RSA 公钥加密失败')
  return encrypted
}

function rsaDecrypt(data, privateKey) {
  const decrypt = new JSEncrypt()
  decrypt.setPrivateKey(privateKey)
  const decrypted = decrypt.decrypt(data)
  if (!decrypted) throw new Error('RSA 私钥解密失败')
  return decrypted
}

function normalizePublicKey(key) {
  return normalizeKey(key, 'PUBLIC KEY')
}

function normalizePrivateKey(key) {
  return normalizeKey(key, 'PRIVATE KEY')
}

function normalizeKey(key, type) {
  const value = String(key || '').trim()
  if (!value) return ''
  if (value.includes('BEGIN')) return value

  const compact = value.replace(/\s+/g, '')
  const lines = compact.match(new RegExp(`.{1,${KEY_LINE_LENGTH}}`, 'g')) || []
  return `-----BEGIN ${type}-----\n${lines.join('\n')}\n-----END ${type}-----`
}
