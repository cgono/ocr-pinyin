import { afterEach, describe, expect, it, vi } from 'vitest'

import { submitProcessRequest } from '../../src/lib/api-client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('submitProcessRequest', () => {
  it('preserves backend error code/message for non-2xx responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 413,
        json: async () => ({
          status: 'error',
          error: {
            code: 'file_too_large',
            message: 'Image is too large. Please upload a smaller file and try again.',
          },
        }),
      }))
    )

    await expect(submitProcessRequest(null)).rejects.toMatchObject({
      code: 'file_too_large',
      message: 'Image is too large. Please upload a smaller file and try again.',
    })
  })

  it('maps in-band error payloads on 2xx responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'error',
          error: {
            code: 'pinyin_provider_unavailable',
            message: 'Pinyin generation is temporarily unavailable.',
          },
        }),
      }))
    )

    await expect(submitProcessRequest(null)).rejects.toMatchObject({
      code: 'pinyin_provider_unavailable',
      message: 'Pinyin generation is temporarily unavailable.',
    })
  })
})
