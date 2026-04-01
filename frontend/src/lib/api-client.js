const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function getHealthStatus() {
  try {
    await fetch(`${API_BASE}/v1/health`)
  } catch {
    // intentionally silent warm-up ping
  }
}

async function parseProcessResponse(response) {
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

  return parseProcessResponse(response)
}

export async function submitTextProcessRequest(sourceText) {
  const response = await fetch(`${API_BASE}/v1/process-text`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ source_text: sourceText }),
  })

  return parseProcessResponse(response)
}
