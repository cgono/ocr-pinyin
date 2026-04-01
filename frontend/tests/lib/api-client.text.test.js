import { afterEach, describe, expect, it, vi } from 'vitest'

import { submitTextProcessRequest } from '../../src/lib/api-client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('submitTextProcessRequest', () => {
  it('posts source text to the process-text endpoint', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'success',
        request_id: 'req_text',
        data: {
          pinyin: {
            segments: [
              {
                source_text: '老师好',
                pinyin_text: 'lǎo shī hǎo',
                alignment_status: 'aligned',
              },
            ],
          },
        },
      }),
    }))
    vi.stubGlobal('fetch', fetchMock)

    const payload = await submitTextProcessRequest('老师好')

    expect(payload.status).toBe('success')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/v1/process-text'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_text: '老师好' }),
      })
    )
  })

  it('maps validation errors from the process-text endpoint', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'error',
          error: {
            code: 'text_empty',
            message: 'Paste some Chinese text to continue.',
          },
        }),
      }))
    )

    await expect(submitTextProcessRequest('   ')).rejects.toMatchObject({
      code: 'text_empty',
      message: 'Paste some Chinese text to continue.',
    })
  })
})
