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
          line_id: 0,
          translation_text: 'Teacher says'
        },
        {
          source_text: '同学们好',
          pinyin_text: 'tóng xué men hǎo',
          alignment_status: 'aligned',
          line_id: 1,
          translation_text: 'Hello, students'
        },
      ]
    },
    job_id: null
  }
}

const GROUPED_PLAYBACK_SUCCESS_RESPONSE = {
  status: 'success',
  request_id: 'req_grouped_playback',
  data: {
    ocr: {
      segments: [
        { text: '老师', language: 'zh', confidence: 0.95, line_id: 0 },
        { text: '叫', language: 'zh', confidence: 0.94, line_id: 0 },
        { text: '同学们好', language: 'zh', confidence: 0.93, line_id: 1 },
      ]
    },
    pinyin: {
      segments: [
        {
          source_text: '老师',
          pinyin_text: 'lǎo shī',
          alignment_status: 'aligned',
          line_id: 0,
          translation_text: 'Teacher calls'
        },
        {
          source_text: '叫',
          pinyin_text: 'jiào',
          alignment_status: 'aligned',
          line_id: 0,
        },
        {
          source_text: '同学们好',
          pinyin_text: 'tóng xué men hǎo',
          alignment_status: 'aligned',
          line_id: 1,
          translation_text: 'Hello, students'
        },
      ]
    },
    job_id: null
  }
}

const DERIVED_READING_SUCCESS_RESPONSE = {
  status: 'success',
  request_id: 'req_reading_projection',
  data: {
    ocr: {
      segments: [
        { text: '老师', language: 'zh', confidence: 0.95, line_id: 0 },
        { text: '好', language: 'zh', confidence: 0.94, line_id: 0 },
        { text: '我们开始上课', language: 'zh', confidence: 0.93, line_id: 1 },
      ]
    },
    pinyin: {
      segments: [
        {
          source_text: '老师',
          pinyin_text: 'lǎo shī',
          alignment_status: 'aligned',
          line_id: 0,
          translation_text: 'teacher'
        },
        {
          source_text: '好',
          pinyin_text: 'hǎo',
          alignment_status: 'aligned',
          line_id: 0,
          translation_text: 'teacher'
        },
        {
          source_text: '我们开始上课',
          pinyin_text: 'wǒ men kāi shǐ shàng kè',
          alignment_status: 'aligned',
          line_id: 1,
          translation_text: 'we begin class'
        },
      ]
    },
    reading: {
      mode: 'derived',
      provider: {
        kind: 'heuristic',
        name: 'built_in_rules',
        version: 'v1',
        applied: true,
        confidence: 0.78,
        warnings: []
      },
      groups: [
        {
          group_id: 'rg_0',
          line_id: 0,
          raw_text: '老师好',
          display_text: '老师，好。',
          playback_text: '老师，好。',
          confidence: 0.78,
          segment_indexes: [0, 1]
        },
        {
          group_id: 'rg_1',
          line_id: 1,
          raw_text: '我们开始上课',
          display_text: '我们开始上课。',
          playback_text: '我们开始上课。',
          confidence: 0.76,
          segment_indexes: [2]
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
          translation_text: null,
          line_id: null
        },
        {
          source_text: '同学们好',
          pinyin_text: 'tóng xué men hǎo',
          alignment_status: 'aligned',
          translation_text: null,
          line_id: null
        },
      ]
    },
    job_id: null
  }
}

const TEXT_MODE_SUCCESS_RESPONSE = {
  status: 'success',
  request_id: 'req_text_mode',
  data: {
    pinyin: {
      segments: [
        {
          source_text: '老师说 Hello',
          pinyin_text: 'lǎo shī shuō   H e l l o',
          alignment_status: 'aligned',
          line_id: 0,
          translation_text: 'Teacher says hello'
        },
        {
          source_text: '同学们好',
          pinyin_text: 'tóng xué men hǎo',
          alignment_status: 'aligned',
          line_id: 1,
          translation_text: 'Hello, students'
        },
      ]
    },
    reading: {
      mode: 'derived',
      provider: {
        kind: 'heuristic',
        name: 'built_in_rules',
        version: 'v2',
        applied: true,
        confidence: 0.8,
        warnings: []
      },
      groups: [
        {
          group_id: 'text_0',
          line_id: 0,
          raw_text: '老师说 Hello',
          display_text: '老师说 Hello。',
          playback_text: '老师说 Hello。',
          confidence: 0.8,
          segment_indexes: [0]
        },
        {
          group_id: 'text_1',
          line_id: 1,
          raw_text: '同学们好',
          display_text: '同学们好。',
          playback_text: '同学们好。',
          confidence: 0.8,
          segment_indexes: [1]
        },
      ]
    },
    job_id: null
  },
  diagnostics: {
    upload_context: {
      content_type: 'text/plain',
      file_size_bytes: 23
    },
    timing: {
      total_ms: 10,
      ocr_ms: 0,
      pinyin_ms: 5
    },
    trace: {
      steps: [
        { step: 'ocr', status: 'skipped' },
        { step: 'pinyin', status: 'ok' },
      ]
    }
  }
}

vi.mock('../../../lib/api-client', () => ({
  submitProcessRequest: vi.fn(async () => DEFAULT_SUCCESS_RESPONSE),
  submitTextProcessRequest: vi.fn(async () => TEXT_MODE_SUCCESS_RESPONSE)
}))

vi.mock('react-image-crop', () => ({
  default: function ReactCropMock({ children, onComplete }) {
    React.useEffect(() => {
      onComplete?.({ x: 0, y: 0, width: 10, height: 10 })
    }, [onComplete])

    return <div data-testid="react-crop">{children}</div>
  },
}))

import { submitProcessRequest, submitTextProcessRequest } from '../../../lib/api-client'

function createSpeechSynthesisMock({ voices = [{ name: 'Chinese Voice', lang: 'zh-CN' }] } = {}) {
  const utterances = []

  function MockSpeechSynthesisUtterance(text) {
    this.text = text
    this.voice = null
    this.lang = ''
    this.onend = null
    this.onerror = null
    utterances.push(this)
  }

  const speechSynthesis = {
    cancel: vi.fn(),
    speak: vi.fn(),
    getVoices: vi.fn(() => voices),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }

  return {
    speechSynthesis,
    MockSpeechSynthesisUtterance,
    utterances,
  }
}

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
  let originalSpeechSynthesis
  let originalSpeechSynthesisUtterance
  let speechMock

  beforeEach(() => {
    submitProcessRequest.mockReset()
    submitProcessRequest.mockImplementation(async () => DEFAULT_SUCCESS_RESPONSE)
    submitTextProcessRequest.mockReset()
    submitTextProcessRequest.mockImplementation(async () => TEXT_MODE_SUCCESS_RESPONSE)
    // P5: save originals so they can be restored after each test
    originalGetContext = globalThis.HTMLCanvasElement.prototype.getContext
    originalToBlob = globalThis.HTMLCanvasElement.prototype.toBlob
    globalThis.HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
      drawImage: vi.fn(),
    }))
    globalThis.HTMLCanvasElement.prototype.toBlob = vi.fn((callback) => {
      callback(new globalThis.Blob(['cropped'], { type: 'image/jpeg' }))
    })
    originalSpeechSynthesis = globalThis.window?.speechSynthesis
    originalSpeechSynthesisUtterance = globalThis.SpeechSynthesisUtterance
    speechMock = createSpeechSynthesisMock()
    globalThis.window.speechSynthesis = speechMock.speechSynthesis
    globalThis.SpeechSynthesisUtterance = speechMock.MockSpeechSynthesisUtterance
  })
  afterEach(() => {
    globalThis.HTMLCanvasElement.prototype.getContext = originalGetContext
    globalThis.HTMLCanvasElement.prototype.toBlob = originalToBlob
    if (originalSpeechSynthesis === undefined) {
      delete globalThis.window.speechSynthesis
    } else {
      globalThis.window.speechSynthesis = originalSpeechSynthesis
    }
    if (originalSpeechSynthesisUtterance === undefined) {
      delete globalThis.SpeechSynthesisUtterance
    } else {
      globalThis.SpeechSynthesisUtterance = originalSpeechSynthesisUtterance
    }
    cleanup()
  })

  it('shows primary take photo and secondary upload actions', () => {
    renderWithClient(<UploadForm />)

    expect(screen.getByRole('button', { name: /take photo/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/upload image/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /paste text/i })).toBeInTheDocument()
  })

  it('submits pasted text through the text endpoint and reuses the reading surface', async () => {
    const user = userEvent.setup()
    const { container } = renderWithClient(<UploadForm />)

    await user.click(screen.getByRole('button', { name: /paste text/i }))
    await user.type(screen.getByLabelText(/paste chinese text/i), '老师说 Hello\n同学们好')
    await user.click(screen.getByRole('button', { name: /^submit$/i }))

    expect(submitTextProcessRequest).toHaveBeenCalledWith('老师说 Hello\n同学们好')
    expect(await screen.findByText(/request id:\s*req_text_mode/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/pinyin-result/i)).toBeInTheDocument()
    expect(screen.queryByAltText(/uploaded image/i)).not.toBeInTheDocument()
    expect(container.querySelectorAll('.pinyin-line-group')).toHaveLength(2)
  })

  it('shows pasted-text validation guidance inline', async () => {
    submitTextProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('empty text'), { code: 'text_empty' })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)

    await user.click(screen.getByRole('button', { name: /paste text/i }))
    await user.click(screen.getByRole('button', { name: /^submit$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/paste some chinese text/i)
  })

  it('shows no-chinese guidance inline for text_no_chinese_text error', async () => {
    submitTextProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('no chinese text'), { code: 'text_no_chinese_text' })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)

    await user.click(screen.getByRole('button', { name: /paste text/i }))
    await user.type(screen.getByLabelText(/paste chinese text/i), 'Hello world')
    await user.click(screen.getByRole('button', { name: /^submit$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/no chinese text was detected/i)
  })

  it('shows too-long guidance inline for text_too_long error', async () => {
    submitTextProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('text too long'), { code: 'text_too_long' })
    )

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)

    await user.click(screen.getByRole('button', { name: /paste text/i }))
    await user.type(screen.getByLabelText(/paste chinese text/i), '你好')
    await user.click(screen.getByRole('button', { name: /^submit$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/text is too long/i)
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

  it('prefers derived reading groups and shows an auto-punctuation note when reading data is applied', async () => {
    submitProcessRequest.mockResolvedValueOnce(DERIVED_READING_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    const { container } = renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await screen.findByLabelText(/pinyin-result/i)

    expect(screen.getByText(/auto-punctuation applied/i)).toBeInTheDocument()
    expect(within(container.querySelectorAll('.pinyin-line-group')[0]).getByText('，')).toBeInTheDocument()
    expect(within(container.querySelectorAll('.pinyin-line-group')[0]).getByText('。')).toBeInTheDocument()
  })

  it('renders translation once per line group with muted styling', async () => {
    submitProcessRequest.mockResolvedValueOnce({
      ...MULTI_LINE_SUCCESS_RESPONSE,
      data: {
        ...MULTI_LINE_SUCCESS_RESPONSE.data,
        pinyin: {
          segments: [
            {
              source_text: '老',
              pinyin_text: 'lǎo',
              alignment_status: 'aligned',
              line_id: 0,
              translation_text: 'teacher'
            },
            {
              source_text: '师',
              pinyin_text: 'shī',
              alignment_status: 'aligned',
              line_id: 0,
              translation_text: 'teacher'
            },
            {
              source_text: '你好',
              pinyin_text: 'nǐ hǎo',
              alignment_status: 'aligned',
              line_id: 1,
              translation_text: 'hello'
            },
          ]
        }
      }
    })

    const user = userEvent.setup()
    const { container } = renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await screen.findByLabelText(/pinyin-result/i)

    const lineGroups = container.querySelectorAll('.pinyin-line-group')
    expect(lineGroups).toHaveLength(2)
    expect(within(lineGroups[0]).getByText('teacher')).toBeInTheDocument()
    expect(within(lineGroups[1]).getByText('hello')).toBeInTheDocument()
    expect(container.querySelectorAll('.pinyin-line-translation')).toHaveLength(2)
    expect(screen.getAllByText('teacher')).toHaveLength(1)
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
    expect(container.querySelectorAll('.pinyin-line-translation')).toHaveLength(0)
    expect(screen.queryByRole('button', { name: /play page pronunciation playback/i })).not.toBeInTheDocument()
  })

  it('renders one pronunciation control per grouped line when playback is supported', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await screen.findByLabelText(/pinyin-result/i)

    expect(screen.getByRole('button', { name: /play pronunciation for 老师叫/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /play pronunciation for 同学们好/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toBeInTheDocument()
  })

  it('speaks grouped source text, stops the active line, and resets after playback ends', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    const playButton = await screen.findByRole('button', { name: /play pronunciation for 老师叫/i })
    await user.click(playButton)

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(1)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)
    expect(speechMock.utterances[0].text).toBe('老师叫')
    expect(screen.getByRole('button', { name: /stop pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'true')

    speechMock.utterances[0].onend?.()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /play pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'false')
    })

    await user.click(screen.getByRole('button', { name: /play pronunciation for 老师叫/i }))
    await user.click(screen.getByRole('button', { name: /stop pronunciation for 老师叫/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(3)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
  })

  it('prefers derived playback_text for line pronunciation controls', async () => {
    submitProcessRequest.mockResolvedValueOnce(DERIVED_READING_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    const playButton = await screen.findByRole('button', { name: /play pronunciation for 老师，好。/i })
    await user.click(playButton)

    expect(speechMock.utterances[0].text).toBe('老师，好。')
  })

  it('cancels the previous utterance before starting playback for another line', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play pronunciation for 老师叫/i }))
    await user.click(screen.getByRole('button', { name: /play pronunciation for 同学们好/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
    expect(speechMock.utterances[1].text).toBe('同学们好')
    expect(screen.getByRole('button', { name: /stop pronunciation for 同学们好/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /play pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'false')
  })

  it('plays grouped lines sequentially from top to bottom and resets after the final line', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(1)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)
    expect(speechMock.utterances[0].text).toBe('老师叫')
    expect(screen.getByRole('button', { name: /stop page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /stop pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'true')

    speechMock.utterances[0].onend?.()
    await waitFor(() => {
      expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
    })

    expect(speechMock.utterances[1].text).toBe('同学们好')
    expect(screen.getByRole('button', { name: /stop pronunciation for 同学们好/i })).toHaveAttribute('aria-pressed', 'true')

    speechMock.utterances[1].onend?.()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'false')
    })

    expect(screen.getByRole('button', { name: /play pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /play pronunciation for 同学们好/i })).toHaveAttribute('aria-pressed', 'false')
  })

  it('prefers derived playback_text for page playback order', async () => {
    submitProcessRequest.mockResolvedValueOnce(DERIVED_READING_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))

    expect(speechMock.utterances[0].text).toBe('老师，好。')

    speechMock.utterances[0].onend?.()
    await waitFor(() => {
      expect(speechMock.utterances[1].text).toBe('我们开始上课。')
    })
  })

  it('queues the next page line after the current onend callback completes', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    let isInsideOnEnd = false
    speechMock.speechSynthesis.speak.mockImplementation((utterance) => {
      if (isInsideOnEnd) {
        return
      }

      const originalOnEnd = utterance.onend
      utterance.onend = (...args) => {
        isInsideOnEnd = true
        try {
          originalOnEnd?.(...args)
        } finally {
          isInsideOnEnd = false
        }
      }
    })

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))

    vi.useFakeTimers()
    try {
      expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)
      speechMock.utterances[0].onend?.()

      expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(0)
      expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
      expect(speechMock.utterances[1].text).toBe('同学们好')
    } finally {
      vi.useRealTimers()
    }
  })

  it('stops page playback immediately and prevents further sequence advancement', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))
    await user.click(screen.getByRole('button', { name: /stop page pronunciation playback/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'false')

    speechMock.utterances[0].onend?.()
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)
  })

  it('switches from page playback to a single line when a line control is pressed', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))
    await user.click(screen.getByRole('button', { name: /play pronunciation for 同学们好/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
    expect(speechMock.utterances[1].text).toBe('同学们好')
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /stop pronunciation for 同学们好/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('switches from line playback to page playback starting from the first line', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play pronunciation for 同学们好/i }))
    await user.click(screen.getByRole('button', { name: /play page pronunciation playback/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
    expect(speechMock.utterances[1].text).toBe('老师叫')
    expect(screen.getByRole('button', { name: /stop page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /stop pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows a non-blocking fallback note and disables pronunciation controls when no Chinese voice is available', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)
    speechMock = createSpeechSynthesisMock({ voices: [{ name: 'English Voice', lang: 'en-US' }] })
    globalThis.window.speechSynthesis = speechMock.speechSynthesis
    globalThis.SpeechSynthesisUtterance = speechMock.MockSpeechSynthesisUtterance

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    const disabledButton = await screen.findByRole('button', { name: /pronunciation unavailable for 老师叫/i })
    expect(disabledButton).toBeDisabled()
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toBeDisabled()
    expect(screen.getByText(/no chinese voice is available/i)).toBeInTheDocument()
  })

  it('shows a non-blocking fallback note when speech synthesis is unsupported', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)
    delete globalThis.window.speechSynthesis
    delete globalThis.SpeechSynthesisUtterance

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    const disabledButton = await screen.findByRole('button', { name: /pronunciation unavailable for 老师叫/i })
    expect(disabledButton).toBeDisabled()
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toBeDisabled()
    expect(screen.getByText(/not supported in this browser/i)).toBeInTheDocument()
  })

  it('renders one pronunciation control per grouped line when playback is supported', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await screen.findByLabelText(/pinyin-result/i)

    expect(screen.getByRole('button', { name: /play pronunciation for 老师叫/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /play pronunciation for 同学们好/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toBeInTheDocument()
  })

  it('speaks grouped source text, stops the active line, and resets after playback ends', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    const playButton = await screen.findByRole('button', { name: /play pronunciation for 老师叫/i })
    await user.click(playButton)

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(1)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)
    expect(speechMock.utterances[0].text).toBe('老师叫')
    expect(screen.getByRole('button', { name: /stop pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'true')

    speechMock.utterances[0].onend?.()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /play pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'false')
    })

    await user.click(screen.getByRole('button', { name: /play pronunciation for 老师叫/i }))
    await user.click(screen.getByRole('button', { name: /stop pronunciation for 老师叫/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(3)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
  })

  it('cancels the previous utterance before starting playback for another line', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play pronunciation for 老师叫/i }))
    await user.click(screen.getByRole('button', { name: /play pronunciation for 同学们好/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
    expect(speechMock.utterances[1].text).toBe('同学们好')
    expect(screen.getByRole('button', { name: /stop pronunciation for 同学们好/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /play pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'false')
  })

  it('plays grouped lines sequentially from top to bottom and resets after the final line', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(1)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)
    expect(speechMock.utterances[0].text).toBe('老师叫')
    expect(screen.getByRole('button', { name: /stop page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /stop pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'true')

    speechMock.utterances[0].onend?.()
    await waitFor(() => {
      expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
    })

    expect(speechMock.utterances[1].text).toBe('同学们好')
    expect(screen.getByRole('button', { name: /stop pronunciation for 同学们好/i })).toHaveAttribute('aria-pressed', 'true')

    speechMock.utterances[1].onend?.()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'false')
    })

    expect(screen.getByRole('button', { name: /play pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /play pronunciation for 同学们好/i })).toHaveAttribute('aria-pressed', 'false')
  })

  it('prefers derived playback_text for page playback order', async () => {
    submitProcessRequest.mockResolvedValueOnce(DERIVED_READING_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))

    expect(speechMock.utterances[0].text).toBe('老师，好。')

    speechMock.utterances[0].onend?.()
    await waitFor(() => {
      expect(speechMock.utterances[1].text).toBe('我们开始上课。')
    })
  })

  it('queues the next page line after the current onend callback completes', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    let isInsideOnEnd = false
    speechMock.speechSynthesis.speak.mockImplementation((utterance) => {
      if (isInsideOnEnd) {
        return
      }

      const originalOnEnd = utterance.onend
      utterance.onend = (...args) => {
        isInsideOnEnd = true
        try {
          originalOnEnd?.(...args)
        } finally {
          isInsideOnEnd = false
        }
      }
    })

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))

    vi.useFakeTimers()
    try {
      expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)
      speechMock.utterances[0].onend?.()

      expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(0)
      expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
      expect(speechMock.utterances[1].text).toBe('同学们好')
    } finally {
      vi.useRealTimers()
    }
  })

  it('stops page playback immediately and prevents further sequence advancement', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))
    await user.click(screen.getByRole('button', { name: /stop page pronunciation playback/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'false')

    speechMock.utterances[0].onend?.()
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(1)
  })

  it('switches from page playback to a single line when a line control is pressed', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play page pronunciation playback/i }))
    await user.click(screen.getByRole('button', { name: /play pronunciation for 同学们好/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
    expect(speechMock.utterances[1].text).toBe('同学们好')
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /stop pronunciation for 同学们好/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('switches from line playback to page playback starting from the first line', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    await user.click(await screen.findByRole('button', { name: /play pronunciation for 同学们好/i }))
    await user.click(screen.getByRole('button', { name: /play page pronunciation playback/i }))

    expect(speechMock.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
    expect(speechMock.speechSynthesis.speak).toHaveBeenCalledTimes(2)
    expect(speechMock.utterances[1].text).toBe('老师叫')
    expect(screen.getByRole('button', { name: /stop page pronunciation playback/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /stop pronunciation for 老师叫/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows a non-blocking fallback note and disables pronunciation controls when no Chinese voice is available', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)
    speechMock = createSpeechSynthesisMock({ voices: [{ name: 'English Voice', lang: 'en-US' }] })
    globalThis.window.speechSynthesis = speechMock.speechSynthesis
    globalThis.SpeechSynthesisUtterance = speechMock.MockSpeechSynthesisUtterance

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    const disabledButton = await screen.findByRole('button', { name: /pronunciation unavailable for 老师叫/i })
    expect(disabledButton).toBeDisabled()
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toBeDisabled()
    expect(screen.getByText(/no chinese voice is available/i)).toBeInTheDocument()
  })

  it('shows a non-blocking fallback note when speech synthesis is unsupported', async () => {
    submitProcessRequest.mockResolvedValueOnce(GROUPED_PLAYBACK_SUCCESS_RESPONSE)
    delete globalThis.window.speechSynthesis
    delete globalThis.SpeechSynthesisUtterance

    const user = userEvent.setup()
    renderWithClient(<UploadForm />)
    const form = screen.getByRole('form', { name: /process-upload-form/i })

    const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/upload image/i), file)
    await user.click(within(form).getByRole('button', { name: /submit/i }))

    const disabledButton = await screen.findByRole('button', { name: /pronunciation unavailable for 老师叫/i })
    expect(disabledButton).toBeDisabled()
    expect(screen.getByRole('button', { name: /play page pronunciation playback/i })).toBeDisabled()
    expect(screen.getByText(/not supported in this browser/i)).toBeInTheDocument()
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
