import React from 'react'
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
        {
          source_text: '你好',
          pinyin_text: 'nǐ hǎo',
          alignment_status: 'aligned',
        },
      ]
    },
    job_id: null
  }
}

const DEFAULT_PARTIAL_RESPONSE = {
  status: 'partial',
  request_id: 'req_partial',
  data: {
    ocr: {
      segments: [{ text: '你好', language: 'zh', confidence: 0.72 }]
    },
  },
  warnings: [
    {
      category: 'pinyin',
      code: 'pinyin_provider_unavailable',
      message: 'Pinyin generation is temporarily unavailable. Please try again.'
    }
  ]
}

const LOW_CONFIDENCE_PARTIAL_RESPONSE = {
  status: 'partial',
  request_id: 'req_low_conf',
  data: {
    ocr: {
      segments: [{ text: '你好', language: 'zh', confidence: 0.45 }]
    },
    pinyin: {
      segments: [
        {
          source_text: '你好',
          pinyin_text: 'nǐ hǎo',
          alignment_status: 'aligned',
        }
      ]
    }
  },
  warnings: [
    {
      category: 'ocr',
      code: 'ocr_low_confidence',
      message: 'OCR confidence is low. Consider retaking the photo for better results.'
    }
  ]
}

const MULTI_LINE_SUCCESS_RESPONSE = {
  status: 'success',
  request_id: 'req_multiline',
  data: {
    ocr: {
      segments: [
        { text: '老师叫', language: 'zh', confidence: 0.95, line_id: 0 },
        { text: '同学们好', language: 'zh', confidence: 0.94, line_id: 1 },
      ]
    },
    pinyin: {
      segments: [
        {
          source_text: '老师叫',
          pinyin_text: 'lǎo shī jiào',
          alignment_status: 'aligned',
          line_id: 0
        },
        {
          source_text: '同学们好',
          pinyin_text: 'tóng xué men hǎo',
          alignment_status: 'aligned',
          line_id: 1
        },
      ]
    },
    job_id: null
  }
}

const NULL_LINE_ID_SUCCESS_RESPONSE = {
  status: 'success',
  request_id: 'req_null_line_id',
  data: {
    ocr: {
      segments: [
        { text: '老师叫', language: 'zh', confidence: 0.95, line_id: null },
        { text: '同学们好', language: 'zh', confidence: 0.94, line_id: null },
      ]
    },
    pinyin: {
      segments: [
        {
          source_text: '老师叫',
          pinyin_text: 'lǎo shī jiào',
          alignment_status: 'aligned',
          line_id: null
        },
        {
          source_text: '同学们好',
          pinyin_text: 'tóng xué men hǎo',
          alignment_status: 'aligned',
          line_id: null
        },
      ]
    },
    job_id: null
  }
}

vi.mock('../../../lib/api-client', () => ({
  submitProcessRequest: vi.fn(async () => DEFAULT_SUCCESS_RESPONSE)
}))

vi.mock('react-image-crop', () => ({
  default: function ReactCropMock({ children, onComplete }) {
    React.useEffect(() => {
      onComplete?.({ x: 0, y: 0, width: 10, height: 10 })
    }, [onComplete])

    return <div data-testid="react-crop">{children}</div>
  },
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
  let originalGetContext
  let originalToBlob

  beforeEach(() => {
    submitProcessRequest.mockReset()
    submitProcessRequest.mockImplementation(async () => DEFAULT_SUCCESS_RESPONSE)
    // P5: save originals so they can be restored after each test
    originalGetContext = globalThis.HTMLCanvasElement.prototype.getContext
    originalToBlob = globalThis.HTMLCanvasElement.prototype.toBlob
    globalThis.HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
      drawImage: vi.fn(),
    }))
    globalThis.HTMLCanvasElement.prototype.toBlob = vi.fn((callback) => {
      callback(new globalThis.Blob(['cropped'], { type: 'image/jpeg' }))
    })
  })
  afterEach(() => {
    globalThis.HTMLCanvasElement.prototype.getContext = originalGetContext
    globalThis.HTMLCanvasElement.prototype.toBlob = originalToBlob
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

    const pinyinResult = await screen.findByLabelText(/pinyin-result/i)
    expect(pinyinResult).toBeInTheDocument()
    expect(screen.getByText('Pinyin Reading')).toBeInTheDocument()
    expect(within(pinyinResult).getByText('你好')).toBeInTheDocument()
    expect(within(pinyinResult).getByText('nǐ hǎo')).toBeInTheDocument()
  })

  it('renders multiline pinyin segments in separate line groups when line ids are present', async () => {
    submitProcessRequest.mockResolvedValueOnce(MULTI_LINE_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    const { container } = renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await screen.findByLabelText(/pinyin-result/i)

    const lineGroups = container.querySelectorAll('.pinyin-line-group')
    expect(lineGroups).toHaveLength(2)
    expect(within(lineGroups[0]).getByText('老师叫')).toBeInTheDocument()
    expect(within(lineGroups[1]).getByText('同学们好')).toBeInTheDocument()
  })

  it('falls back to flat pinyin rendering when all line ids are null', async () => {
    submitProcessRequest.mockResolvedValueOnce(NULL_LINE_ID_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    const { container } = renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    const pinyinResult = await screen.findByLabelText(/pinyin-result/i)

    expect(container.querySelectorAll('.pinyin-line-group')).toHaveLength(0)
    expect(within(pinyinResult).getByText('老师叫')).toBeInTheDocument()
    expect(within(pinyinResult).getByText('同学们好')).toBeInTheDocument()
    expect(container.querySelectorAll('ruby')).toHaveLength(2)
  })

  it('shows uncertain segments explicitly when alignment fails for one segment', async () => {
    submitProcessRequest.mockResolvedValueOnce({
      ...DEFAULT_SUCCESS_RESPONSE,
      data: {
        ...DEFAULT_SUCCESS_RESPONSE.data,
        pinyin: {
          segments: [
            {
              source_text: '你好',
              pinyin_text: 'nǐ hǎo',
              alignment_status: 'aligned'
            },
            {
              source_text: '世界',
              pinyin_text: '',
              alignment_status: 'uncertain',
              reason_code: 'pinyin_execution_failed'
            },
          ]
        }
      }
    })

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByText('世界')).toBeInTheDocument()
    expect(screen.getByText('Uncertain pronunciation')).toBeInTheDocument()
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
    expect(screen.getByText(/show details/i)).toBeInTheDocument()
    const detailsEl = document.querySelector('details')
    expect(detailsEl).not.toBeNull()
    expect(within(detailsEl).getByText(/你好/)).toBeInTheDocument()
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

  it('shows crop preview for camera capture without immediate submit', async () => {
    renderWithClient(<UploadForm />)

    const cameraInput = document.querySelector('input[capture="environment"]')
    expect(cameraInput).not.toBeNull()

    const file = new globalThis.File(['camera-bytes'], 'camera.jpg', { type: 'image/jpeg' })
    await userEvent.upload(cameraInput, file)

    expect(screen.getByLabelText(/crop-preview/i)).toBeInTheDocument()
    expect(submitProcessRequest).not.toHaveBeenCalled()
    expect(screen.queryByText(/waiting for submission/i)).not.toBeInTheDocument()
  })

  it('dismisses crop preview back to idle without submitting', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)

    const cameraInput = document.querySelector('input[capture="environment"]')
    const file = new globalThis.File(['camera-bytes'], 'camera.jpg', { type: 'image/jpeg' })
    await user.upload(cameraInput, file)
    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(submitProcessRequest).not.toHaveBeenCalled()
    expect(screen.getByText(/waiting for submission/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/crop-preview/i)).not.toBeInTheDocument()
  })

  it('shows loading spinner while upload is pending', async () => {
    let resolveRequest
    submitProcessRequest.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveRequest = () => resolve(DEFAULT_SUCCESS_RESPONSE)
      })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(screen.getByText(/uploading image/i)).toBeInTheDocument()
    expect(document.querySelector('.loading-spinner')).not.toBeNull()

    resolveRequest()
    expect(await screen.findByLabelText(/processing-complete/i)).toBeInTheDocument()
  })

  it('shows loading spinner while camera crop upload is pending', async () => {
    let resolveRequest
    submitProcessRequest.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveRequest = () => resolve(DEFAULT_SUCCESS_RESPONSE)
      })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)

    const cameraInput = document.querySelector('input[capture="environment"]')
    const file = new globalThis.File(['camera-bytes'], 'camera.jpg', { type: 'image/jpeg' })
    await user.upload(cameraInput, file)
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    expect(await screen.findByText(/uploading image/i)).toBeInTheDocument()
    expect(document.querySelector('.loading-spinner')).not.toBeNull()

    resolveRequest()
    expect(await screen.findByLabelText(/processing-complete/i)).toBeInTheDocument()
  })

  it('submits cropped camera image after confirmation', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)

    const cameraInput = document.querySelector('input[capture="environment"]')
    const file = new globalThis.File(['camera-bytes'], 'camera.jpg', { type: 'image/jpeg' })
    await user.upload(cameraInput, file)
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    await waitFor(() => {
      expect(submitProcessRequest).toHaveBeenCalledTimes(1)
    })
    expect(submitProcessRequest.mock.calls[0][0]).toBeInstanceOf(globalThis.File)
    expect(await screen.findByLabelText(/processing-complete/i)).toBeInTheDocument()
  })

  it('shows warning guidance when partial response includes pinyin failure warning', async () => {
    submitProcessRequest.mockResolvedValueOnce(DEFAULT_PARTIAL_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByLabelText(/processing-partial/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/processing-warnings/i)).toBeInTheDocument()
    expect(screen.getByText(/pinyin generation is temporarily unavailable/i)).toBeInTheDocument()
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

  it('shows low-confidence guidance with retake and proceed options when confidence is low', async () => {
    submitProcessRequest.mockResolvedValueOnce(LOW_CONFIDENCE_PARTIAL_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByLabelText(/low-confidence-guidance/i)).toBeInTheDocument()
    expect(screen.getByText(/ocr confidence is low/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retake photo/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /use this result anyway/i })).toBeInTheDocument()
  })

  it('hides low-confidence guidance and shows result when use this result anyway is clicked', async () => {
    submitProcessRequest.mockResolvedValueOnce(LOW_CONFIDENCE_PARTIAL_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await screen.findByLabelText(/low-confidence-guidance/i)
    await user.click(screen.getByRole('button', { name: /use this result anyway/i }))

    expect(screen.queryByLabelText(/low-confidence-guidance/i)).not.toBeInTheDocument()
    // Pinyin result is still visible after dismissal
    expect(screen.getByLabelText(/pinyin-result/i)).toBeInTheDocument()
  })

  it('requires manual resubmission when a new upload file is selected after low confidence', async () => {
    submitProcessRequest
      .mockResolvedValueOnce(LOW_CONFIDENCE_PARTIAL_RESPONSE)
      .mockResolvedValueOnce(DEFAULT_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })
    const uploadInput = screen.getByLabelText(/upload image/i)

    const firstFile = new globalThis.File(['img-bytes'], 'first.jpg', { type: 'image/jpeg' })
    await user.upload(uploadInput, firstFile)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    expect(await screen.findByLabelText(/low-confidence-guidance/i)).toBeInTheDocument()
    expect(submitProcessRequest).toHaveBeenCalledTimes(1)

    const retryFile = new globalThis.File(['retry-bytes'], 'retry.jpg', { type: 'image/jpeg' })
    await user.upload(uploadInput, retryFile)

    expect(submitProcessRequest).toHaveBeenCalledTimes(1)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await waitFor(() => {
      expect(submitProcessRequest).toHaveBeenCalledTimes(2)
    })
    expect(submitProcessRequest).toHaveBeenLastCalledWith(retryFile)
    expect(await screen.findByLabelText(/processing-complete/i)).toBeInTheDocument()
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

describe('UploadForm styling and accessibility', () => {
  beforeEach(() => {
    submitProcessRequest.mockReset()
    submitProcessRequest.mockImplementation(async () => DEFAULT_SUCCESS_RESPONSE)
  })
  afterEach(() => {
    cleanup()
  })

  it('renders upload actions and status panel with semantic class structure', () => {
    renderWithClient(<UploadForm />)
    expect(document.querySelector('.upload-actions')).toBeInTheDocument()
    expect(document.querySelector('.status-panel')).toBeInTheDocument()
    expect(document.querySelector('.status-panel--idle')).toBeInTheDocument()
  })

  it('applies loading state class while processing', async () => {
    let release
    submitProcessRequest.mockImplementationOnce(
      () => new Promise((resolve) => { release = resolve })
    )
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(screen.getByRole('button', { name: /submit/i }))
    await screen.findByText((_, element) => element?.textContent === 'Uploading image...')
    expect(document.querySelector('.status-panel--loading')).toBeInTheDocument()
    release(DEFAULT_SUCCESS_RESPONSE)
  })

  it('applies success state class after processing completes', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(screen.getByRole('button', { name: /submit/i }))
    await screen.findByLabelText(/processing-complete/i)
    expect(document.querySelector('.status-panel--success')).toBeInTheDocument()
  })

  it('applies partial state class when processing returns a partial result', async () => {
    submitProcessRequest.mockResolvedValueOnce(DEFAULT_PARTIAL_RESPONSE)
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(screen.getByRole('button', { name: /submit/i }))
    await screen.findByLabelText(/processing-partial/i)
    expect(document.querySelector('.status-panel--partial')).toBeInTheDocument()
    expect(screen.getByText(/status:\s*partial/i)).toBeInTheDocument()
  })

  it('applies error state class when processing fails', async () => {
    submitProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('bad image'), { code: 'image_decode_failed' })
    )
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const file = new globalThis.File(['img-bytes'], 'bad.png', { type: 'image/png' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(screen.getByRole('button', { name: /submit/i }))
    await screen.findByRole('alert')
    expect(document.querySelector('.status-panel--error')).toBeInTheDocument()
  })

  it('uses semantic class on pinyin result content for typography styling', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(screen.getByRole('button', { name: /submit/i }))
    await screen.findByLabelText(/pinyin-result/i)
    expect(document.querySelector('.pinyin-result__content')).toBeInTheDocument()
  })

  it('renders OCR details in a collapsed details element with semantic class', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(screen.getByRole('button', { name: /submit/i }))
    await screen.findByLabelText(/result-view/i)
    const detailsEl = document.querySelector('details')
    expect(detailsEl).toBeInTheDocument()
    expect(detailsEl).not.toHaveAttribute('open')
    expect(detailsEl).toHaveClass('details-section')
  })

  it('key content is accessible in the document after successful processing', async () => {
    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(screen.getByRole('button', { name: /submit/i }))

    await screen.findByLabelText(/result-view/i)
    // Primary actions remain accessible
    expect(screen.getByRole('button', { name: /take photo/i })).toBeInTheDocument()
    // Pinyin content is accessible
    expect(screen.getByLabelText(/pinyin-result/i)).toBeInTheDocument()
    // Details toggle is accessible
    expect(screen.getByText(/show details/i)).toBeInTheDocument()
  })
})
