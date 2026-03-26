import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@sentry/react', () => ({
  init: vi.fn(),
  ErrorBoundary: ({ children }) => children,
  browserTracingIntegration: vi.fn(() => ({})),
}))

import App from '../App'

function renderWithClient(ui) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('Sentry integration', () => {
  it('renders without crashing when sentry dsn is missing', () => {
    expect(() => renderWithClient(<App />)).not.toThrow()
  })
})
