/**
 * 后端 API 封装层。
 * 开发环境通过 vite proxy 代理到 localhost:8000，无 CORS 问题。
 */

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

// ---- 查询 ----
export function fetchCalendar(startDate, endDate, { games, owners, keyword } = {}) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
  if (games) params.set('games', games)
  if (owners) params.set('owners', owners)
  if (keyword) params.set('keyword', keyword)
  return request(`/calendar?${params}`)
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
