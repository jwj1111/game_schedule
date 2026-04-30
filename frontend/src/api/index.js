/**
 * 后端 API 封装层。
 * 开发环境通过 vite proxy 代理到 localhost:8000，无 CORS 问题。
 */

const BASE = '/api'
const TOKEN_KEY = 'game_schedule_admin_token'

function readStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch (e) {
    console.warn('读取管理员 token 失败:', e)
    return ''
  }
}

function writeStoredToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch (e) {
    console.warn('写入管理员 token 失败:', e)
  }
}

let unauthorizedHandler = null
let authToken = readStoredToken()

export function getAuthToken() {
  return authToken
}

export function setAuthToken(token) {
  authToken = token || ''
  writeStoredToken(authToken)
}

export function clearAuthToken() {
  setAuthToken('')
}

export function onAuthUnauthorized(handler) {
  unauthorizedHandler = handler
}

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  if (authToken) headers.Authorization = `Bearer ${authToken}`

  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      ...options,
      headers,
    })
  } catch (e) {
    const err = new Error('网络连接失败，请稍后重试')
    err.status = 0
    err.cause = e
    throw err
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    const err = new Error(errBody.detail || `HTTP ${res.status}`)
    err.status = res.status
    if ((res.status === 401 || res.status === 403) && !path.startsWith('/auth/login')) {
      clearAuthToken()
      unauthorizedHandler?.(err)
    }
    throw err
  }
  if (res.status === 204) return null
  return res.json()
}

// ---- 认证 ----
export function loginAdmin(password) {
  return request('/auth/login', { method: 'POST', body: JSON.stringify({ password }) })
}

export function fetchAuthStatus() {
  return request('/auth/status')
}

export function logoutAdmin() {
  return request('/auth/logout', { method: 'POST' })
}

// ---- 查询 ----
export function fetchCalendar(startDate, endDate, { games, owners, keyword } = {}) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
  if (games) params.set('games', games)
  if (owners) params.set('owners', owners)
  if (keyword) params.set('keyword', keyword)
  return request(`/calendar?${params}`)
}

export function fetchOverview() {
  return request('/overview')
}

export function fetchGames() {
  return request('/games')
}

export function fetchOwnerNames() {
  return request('/owner-names')
}

export function fetchHidden() {
  return request('/hidden')
}

// ---- 标注 ----
export function updateAnnotation(newsId, data) {
  return request(`/annotations/${newsId}`, { method: 'PUT', body: JSON.stringify(data) })
}

// ---- 事件 ----
export function createEvent(data) {
  return request('/events', { method: 'POST', body: JSON.stringify(data) })
}

export function updateEvent(id, data) {
  return request(`/events/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}

export function deleteEvent(id) {
  return request(`/events/${id}`, { method: 'DELETE' })
}

// ---- 负责人 ----
export function fetchOwners() {
  return request('/owners')
}

export function createOwner(data) {
  return request('/owners', { method: 'POST', body: JSON.stringify(data) })
}

export function updateOwner(game, data) {
  return request(`/owners/${encodeURIComponent(game)}`, { method: 'PUT', body: JSON.stringify(data) })
}
