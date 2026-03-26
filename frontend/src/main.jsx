import React from 'react'
import * as Sentry from '@sentry/react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import './styles/main.css'
import App from './App'

function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) {
    return
  }

  try {
    Sentry.init({
      dsn,
      environment: import.meta.env.VITE_APP_ENV || 'development',
      release: import.meta.env.VITE_APP_VERSION || '0.1.0',
      tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 1.0),
      integrations: [Sentry.browserTracingIntegration()],
    })
  } catch (error) {
    console.warn('Sentry initialization failed; monitoring disabled.', error)
  }
}

initSentry()

const queryClient = new QueryClient()

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
)
