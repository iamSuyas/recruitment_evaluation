const BASE = '/api'

function getToken() {
  return localStorage.getItem('tk_token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('tk_token')
    localStorage.removeItem('tk_user')
    window.location.href = '/login'
    return
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  login: (email, password) => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    return fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Login failed')
      }
      return res.json()
    })
  },

  register: (email, password) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  getCandidates: (params = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v) })
    return request(`/candidates?${q}`)
  },

  getCandidate: (id) => request(`/candidates/${id}`),

  submitScore: (id, data) =>
    request(`/candidates/${id}/scores`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  generateSummary: (id) =>
    request(`/candidates/${id}/summary`, { method: 'POST' }),

  updateNotes: (id, internal_notes) =>
    request(`/candidates/${id}/notes`, {
      method: 'PATCH',
      body: JSON.stringify({ internal_notes }),
    }),

  deleteCandidate: (id) =>
    request(`/candidates/${id}`, { method: 'DELETE' }),
}