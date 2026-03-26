import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'

import DiagnosticsPanel from '../../../features/process/components/DiagnosticsPanel'

const MOCK_DIAGNOSTICS = {
  upload_context: { content_type: 'image/png', file_size_bytes: 4096 },
  timing: { total_ms: 823.4, ocr_ms: 612.1, pinyin_ms: 98.7 },
  trace: {
    steps: [
      { step: 'ocr', status: 'ok' },
      { step: 'pinyin', status: 'ok' },
      { step: 'confidence_check', status: 'ok' },
    ]
  }
}

const MOCK_OCR_SEGMENTS = [
  { text: '你好', language: 'zh', confidence: 0.98 }
]

afterEach(() => {
  cleanup()
})

describe('DiagnosticsPanel', () => {
  it('is collapsed by default with show details summary text', () => {
    render(<DiagnosticsPanel diagnostics={MOCK_DIAGNOSTICS} ocrSegments={MOCK_OCR_SEGMENTS} />)

    const detailsEl = document.querySelector('details[aria-label="diagnostics-panel"]')

    expect(detailsEl).toBeInTheDocument()
    expect(detailsEl).not.toHaveAttribute('open')
    expect(screen.getByText('Show Details')).toBeInTheDocument()
  })

  it('shows OCR segments when expanded', async () => {
    const user = userEvent.setup()
    render(<DiagnosticsPanel diagnostics={null} ocrSegments={MOCK_OCR_SEGMENTS} />)

    await user.click(screen.getByText('Show Details'))

    const detailsEl = screen.getByLabelText('diagnostics-panel')
    expect(within(detailsEl).getByText('你好')).toBeInTheDocument()
    expect(within(detailsEl).getByText(/\(zh, 98%\)/i)).toBeInTheDocument()
  })

  it('shows timing when diagnostics is provided', async () => {
    const user = userEvent.setup()
    render(<DiagnosticsPanel diagnostics={MOCK_DIAGNOSTICS} ocrSegments={MOCK_OCR_SEGMENTS} />)

    await user.click(screen.getByText('Show Details'))

    expect(screen.getByText('Timing')).toBeInTheDocument()
    expect(screen.getByText(/823\.4ms/i)).toBeInTheDocument()
    expect(screen.getByText(/612\.1ms/i)).toBeInTheDocument()
    expect(screen.getByText(/98\.7ms/i)).toBeInTheDocument()
  })

  it('shows trace steps when diagnostics is provided', async () => {
    const user = userEvent.setup()
    render(<DiagnosticsPanel diagnostics={MOCK_DIAGNOSTICS} ocrSegments={MOCK_OCR_SEGMENTS} />)

    await user.click(screen.getByText('Show Details'))

    expect(screen.getByText('Trace')).toBeInTheDocument()
    expect(screen.getByText(/ocr: ok/i)).toBeInTheDocument()
    expect(screen.getByText(/pinyin: ok/i)).toBeInTheDocument()
    expect(screen.getByText(/confidence_check: ok/i)).toBeInTheDocument()
  })

  it('hides timing when diagnostics is absent', async () => {
    const user = userEvent.setup()
    render(<DiagnosticsPanel diagnostics={null} ocrSegments={MOCK_OCR_SEGMENTS} />)

    await user.click(screen.getByText('Show Details'))

    expect(screen.queryByText('Timing')).not.toBeInTheDocument()
    expect(screen.queryByText('Trace')).not.toBeInTheDocument()
  })

  it('returns null when there is no data', () => {
    const { container } = render(<DiagnosticsPanel diagnostics={null} ocrSegments={[]} />)

    expect(container).toBeEmptyDOMElement()
    expect(document.querySelector('details')).toBeNull()
  })

  it('uses the details-section class', () => {
    render(<DiagnosticsPanel diagnostics={MOCK_DIAGNOSTICS} ocrSegments={MOCK_OCR_SEGMENTS} />)

    expect(screen.getByLabelText('diagnostics-panel')).toHaveClass('details-section')
  })

  it('shows timing and trace when diagnostics provided but ocrSegments is empty', async () => {
    const user = userEvent.setup()
    render(<DiagnosticsPanel diagnostics={MOCK_DIAGNOSTICS} ocrSegments={[]} />)

    await user.click(screen.getByText('Show Details'))

    expect(screen.queryByText('OCR Details')).not.toBeInTheDocument()
    expect(screen.getByText('Timing')).toBeInTheDocument()
    expect(screen.getByText('Trace')).toBeInTheDocument()
  })
})
