const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function submitProcessRequest(file) {
  const headers = {}
  if (file?.type) {
    headers['Content-Type'] = file.type
  }

  const response = await fetch(`${API_BASE}/v1/process`, {
    method: 'POST',
    headers,
    body: file || undefined
  })

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    const error = new Error(payload?.error?.message || `Request failed with status ${response.status}`)
    error.code = payload?.error?.code || 'http_error'
    throw error
  }

  if (payload?.status === 'error') {
    const error = new Error(payload.error?.message || 'Upload failed')
    error.code = payload.error?.code || 'unknown_error'
    throw error
  }

  return payload
}
