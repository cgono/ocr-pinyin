import { useEffect } from 'react'
import { ErrorBoundary } from '@sentry/react'

import { getHealthStatus } from './lib/api-client'
import UploadForm from './features/process/components/UploadForm'

function ErrorFallback() {
  return <p className="error-fallback">Something went wrong.</p>
}

export default function App() {
  useEffect(() => {
    getHealthStatus().catch(() => {})
  }, [])

  return (
    <ErrorBoundary fallback={<ErrorFallback />}>
      <main className="app-shell">
        <h1 className="app-title">Process Image</h1>
        <UploadForm />
      </main>
    </ErrorBoundary>
  )
}
