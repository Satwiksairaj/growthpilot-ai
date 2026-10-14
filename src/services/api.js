const configuredOrigin = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '')
const BASE = configuredOrigin
  ? `${/^[a-z][a-z\d+.-]*:\/\//i.test(configuredOrigin) ? configuredOrigin : `https://${configuredOrigin}`}${configuredOrigin.endsWith('/api') ? '' : '/api'}`
  : '/api'

async function requestJSON(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })

  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((issue) => issue.msg).filter(Boolean).join(' ') || message
      }
    } catch {
      // Keep the HTTP status text when the server did not return JSON.
    }
    throw new Error(message || `Request failed with status ${res.status}`)
  }

  if (res.status === 204) return null
  return res.json()
}

export function submitAssessment(payload, idempotencyKey) {
  return requestJSON('/assessments', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  })
}

export function trackVisit(payload) {
  return requestJSON('/visits', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchMetrics() {
  return requestJSON('/metrics')
}

export default { submitAssessment, trackVisit, fetchMetrics }
