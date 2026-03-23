import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import UploadForm from '../../../features/process/components/UploadForm'

const DEFAULT_SUCCESS_RESPONSE = {
  status: 'success',
  request_id: 'req_test',
  data: {
    ocr: {
      segments: [{ text: '你好', language: 'zh', confidence: 0.98 }]
    },
    pinyin: {
      segments: [
        { hanzi: '你', pinyin: 'nǐ' },
        { hanzi: '好', pinyin: 'hǎo' },
      ]
    },
    job_id: null
  }
}

vi.mock('../../../lib/api-client', () => ({
  submitProcessRequest: vi.fn(async () => DEFAULT_SUCCESS_RESPONSE)
}))

import { submitProcessRequest } from '../../../lib/api-client'

function renderWithClient(ui) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('UploadForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(() => {
    cleanup()
  })

  it('shows primary take photo and secondary upload actions', () => {
    renderWithClient(<UploadForm />)

    expect(screen.getByRole('button', { name: /take photo/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/upload image/i)).toBeInTheDocument()
  })

  it('submits to process endpoint through api client', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(submitProcessRequest).toHaveBeenCalledTimes(1)
    expect(await screen.findByText(/status:\s*success/i)).toBeInTheDocument()
    expect(screen.getByText(/request id:\s*req_test/i)).toBeInTheDocument()
  })

  it('shows actionable guidance when validation fails', async () => {
    submitProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('bad image'), { code: 'image_decode_failed' })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['bad-bytes'], 'bad.png', { type: 'image/png' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/could not read that image/i)
  })

  it('shows pinyin reading result when extraction succeeds', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByLabelText(/pinyin-result/i)).toBeInTheDocument()
    expect(screen.getByText('Pinyin Reading')).toBeInTheDocument()
    // Characters are rendered as ruby elements
    expect(screen.getByText('你')).toBeInTheDocument()
    expect(screen.getByText('好')).toBeInTheDocument()
    // Pinyin readings are rendered as rt elements
    expect(screen.getByText('nǐ')).toBeInTheDocument()
    expect(screen.getByText('hǎo')).toBeInTheDocument()
  })

  it('shows explicit completion state when processing succeeds', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByLabelText(/processing-complete/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/processing-complete/i)).toHaveTextContent(/processing complete/i)
  })

  it('shows unified result view with image and pinyin together', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(screen.getByRole('button', { name: /submit/i }))

    await waitFor(() => {
      expect(screen.getByLabelText(/result-view/i)).toBeInTheDocument()
    })

    const resultView = screen.getByLabelText(/result-view/i)
    // Image and pinyin are both present inside the unified result view
    expect(within(resultView).getByRole('img', { name: /uploaded image/i })).toBeInTheDocument()
    expect(within(resultView).getByLabelText(/pinyin-result/i)).toBeInTheDocument()
  })

  it('shows OCR details in secondary collapsed section', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await screen.findByLabelText(/result-view/i)
    // OCR details available in a disclosure widget (secondary)
    expect(screen.getByText(/extracted text/i)).toBeInTheDocument()
    expect(screen.getByText(/你好/)).toBeInTheDocument()
    expect(screen.getByText(/zh, 98%/i)).toBeInTheDocument()
  })

  it('shows pinyin retry guidance when pinyin fails', async () => {
    submitProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('pinyin unavailable'), { code: 'pinyin_provider_unavailable' })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /pinyin generation is temporarily unavailable/i
    )
  })

  it('shows OCR retry guidance when OCR fails', async () => {
    submitProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('OCR no text'), { code: 'ocr_no_text_detected' })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/no readable chinese text detected/i)
    expect(screen.getByRole('button', { name: /take photo/i })).toBeInTheDocument()
  })

  it('shows progress state while valid upload is being processed', async () => {
    let release
    submitProcessRequest.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          release = resolve
        })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByText(/uploading image/i)).toBeInTheDocument()

    release(DEFAULT_SUCCESS_RESPONSE)

    await waitFor(() => {
      expect(screen.getByText(/status:\s*success/i)).toBeInTheDocument()
    })
  })

  it('shows fallback error message for unrecognised validation code', async () => {
    submitProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('An unexpected server error occurred'), { code: 'internal_server_error' })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    // code not in recoveryGuidanceByCode -> falls back to error.message
    expect(await screen.findByRole('alert')).toHaveTextContent(/unexpected server error occurred/i)
  })
})

