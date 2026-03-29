import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

const { getHealthStatus } = vi.hoisted(() => ({
  getHealthStatus: vi.fn(() => Promise.resolve()),
}))

vi.mock('@sentry/react', () => ({
  ErrorBoundary: ({ children }) => children,
}))

vi.mock('../features/process/components/UploadForm', () => ({
  default: () => <div>Upload Form</div>,
}))

vi.mock('../lib/api-client', () => ({
  getHealthStatus,
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

describe('App', () => {
  it('fires a silent health ping on mount', async () => {
    getHealthStatus.mockClear()
    renderWithClient(<App />)

    await waitFor(() => {
      expect(getHealthStatus).toHaveBeenCalledTimes(1)
    })
  })

  it('silently ignores health ping failure with no error UI and form remains usable (AC-6)', async () => {
    getHealthStatus.mockRejectedValue(new Error('Network error'))
    renderWithClient(<App />)

    await waitFor(() => {
      expect(getHealthStatus).toHaveBeenCalled()
    })

    // No error boundary triggered — upload form is still rendered
    expect(screen.getAllByText('Upload Form').length).toBeGreaterThan(0)
  })
})
