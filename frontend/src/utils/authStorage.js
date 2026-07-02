const AUTH_TOKEN_KEY = 'auth_token'
const AUTH_USERNAME_KEY = 'auth_username'
const AUTH_USER_ID_KEY = 'auth_user_id'
const AUTH_USER_CODE_KEY = 'auth_user_code'
const AUTH_SESSION_OK_KEY = 'auth_session_ok'

const LEGACY_KEYS = [
  AUTH_TOKEN_KEY,
  AUTH_USERNAME_KEY,
  AUTH_USER_ID_KEY,
  AUTH_USER_CODE_KEY,
]

function readSession(key) {
  return sessionStorage.getItem(key) || ''
}

export function getAuthToken() {
  return readSession(AUTH_TOKEN_KEY)
}

export function getAuthUsername() {
  return readSession(AUTH_USERNAME_KEY)
}

export function getAuthUserId() {
  return readSession(AUTH_USER_ID_KEY)
}

export function getAuthUserCode() {
  return readSession(AUTH_USER_CODE_KEY)
}

export function isAuthSessionReady() {
  return sessionStorage.getItem(AUTH_SESSION_OK_KEY) === '1'
}

export function saveAuthSession({ token, username, userId, userCode }) {
  sessionStorage.setItem(AUTH_TOKEN_KEY, token || '')
  sessionStorage.setItem(AUTH_USERNAME_KEY, username || '')
  sessionStorage.setItem(AUTH_USER_ID_KEY, userId != null ? String(userId) : '')
  sessionStorage.setItem(AUTH_USER_CODE_KEY, userCode || '')
  sessionStorage.setItem(AUTH_SESSION_OK_KEY, '1')
}

export function updateAuthUserInfo({ username, userId, userCode }) {
  if (username !== undefined) {
    sessionStorage.setItem(AUTH_USERNAME_KEY, username || '')
  }
  if (userId !== undefined) {
    sessionStorage.setItem(AUTH_USER_ID_KEY, userId != null ? String(userId) : '')
  }
  if (userCode !== undefined) {
    sessionStorage.setItem(AUTH_USER_CODE_KEY, userCode || '')
  }
}

export function clearAuthSession() {
  sessionStorage.removeItem(AUTH_TOKEN_KEY)
  sessionStorage.removeItem(AUTH_USERNAME_KEY)
  sessionStorage.removeItem(AUTH_USER_ID_KEY)
  sessionStorage.removeItem(AUTH_USER_CODE_KEY)
  sessionStorage.removeItem(AUTH_SESSION_OK_KEY)
}

export function clearLegacySharedAuth() {
  for (const key of LEGACY_KEYS) {
    localStorage.removeItem(key)
  }
}

export function bootstrapLegacyAuth() {
  if (isAuthSessionReady()) {
    clearLegacySharedAuth()
    return
  }

  const legacyToken = localStorage.getItem(AUTH_TOKEN_KEY)
  if (!legacyToken) {
    clearLegacySharedAuth()
    return
  }

  saveAuthSession({
    token: legacyToken,
    username: localStorage.getItem(AUTH_USERNAME_KEY) || '',
    userId: localStorage.getItem(AUTH_USER_ID_KEY) || '',
    userCode: localStorage.getItem(AUTH_USER_CODE_KEY) || '',
  })
  clearLegacySharedAuth()
}
