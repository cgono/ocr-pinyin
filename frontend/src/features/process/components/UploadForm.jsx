import { useEffect, useRef, useState } from 'react'

import { useMutation } from '@tanstack/react-query'

import { submitProcessRequest } from '../../../lib/api-client'

const recoveryGuidanceByCode = {
  missing_file: 'No photo detected. Tap Take Photo or choose an image to continue.',
  invalid_mime_type: 'Unsupported file type. Retake or upload a JPG, PNG, or WEBP image.',
  file_too_large: 'Image is too large. Retake with a lower resolution or upload a smaller file.',
  image_decode_failed: 'We could not read that image. Retake a clearer photo and try again.',
  image_too_large_pixels: 'Image dimensions are too large. Retake with lower resolution and retry.',
  ocr_execution_failed: 'Text extraction encountered an error. Tap Take Photo to retry.',
  ocr_no_text_detected: 'No readable Chinese text detected. Retake the photo and try again.',
  ocr_provider_unavailable: 'Text extraction is temporarily unavailable. Tap Take Photo to retry.',
  pinyin_provider_unavailable: 'Pinyin generation is temporarily unavailable. Tap Submit to retry.',
  pinyin_execution_failed: 'Pinyin generation encountered an error. Tap Submit to retry.',
}

function formatConfidence(confidence) {
  return `${Math.round(confidence * 100)}%`
}

export default function UploadForm() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const cameraInputRef = useRef(null)

  // Create and revoke object URL when file changes
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const mutation = useMutation({
    mutationFn: () => submitProcessRequest(file),
  })

  const handleSubmit = (event) => {
    event.preventDefault()
    mutation.mutate()
  }

  const pinyinSegments = mutation.data?.data?.pinyin?.segments || []
  const ocrSegments = mutation.data?.data?.ocr?.segments || []

  return (
    <section>
      {/* Hidden file input with camera capture for "Take Photo" */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        aria-hidden="true"
        onChange={(event) => setFile(event.target.files?.[0] || null)}
      />

      <form onSubmit={handleSubmit} aria-label="process-upload-form">
        <button
          type="button"
          onClick={() => cameraInputRef.current?.click()}
        >
          Take Photo
        </button>
        <div style={{ marginTop: '0.75rem' }}>
          <label htmlFor="upload-image">Upload image</label>
          <input
            id="upload-image"
            name="upload-image"
            type="file"
            accept="image/*"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </div>
        <button type="submit" disabled={mutation.isPending} style={{ marginTop: '0.75rem' }}>
          {mutation.isPending ? 'Submitting...' : 'Submit'}
        </button>
      </form>

      <div style={{ marginTop: '1rem' }}>
        <h2>Processing Status</h2>
        {!mutation.data && !mutation.error && !mutation.isPending && <p>Waiting for submission.</p>}
        {mutation.isPending && <p>Uploading image...</p>}
        {mutation.error && (
          <p role="alert">
            {recoveryGuidanceByCode[mutation.error.code] || mutation.error.message}
          </p>
        )}

        {mutation.data && (
          <div>
            {mutation.data.status === 'success' && (
              <p aria-label="processing-complete">
                ✓ Processing complete
              </p>
            )}
            <p>Status: {mutation.data.status}</p>
            <p>Request ID: {mutation.data.request_id}</p>

            {/* Unified result: image + pinyin reading together */}
            {(previewUrl || pinyinSegments.length > 0) && (
              <div aria-label="result-view" style={{ marginTop: '1rem' }}>
                {previewUrl && (
                  <div>
                    <img
                      src={previewUrl}
                      alt="Uploaded image"
                      style={{ maxWidth: '100%', maxHeight: 320, display: 'block', marginBottom: '1rem' }}
                    />
                  </div>
                )}

                {pinyinSegments.length > 0 && (
                  <div aria-label="pinyin-result">
                    <h3>Pinyin Reading</h3>
                    <div style={{ fontSize: '1.4rem', lineHeight: 2.5, wordBreak: 'break-all' }}>
                      {pinyinSegments.map((seg, index) => (
                        <ruby key={`${seg.hanzi}-${index}`}>
                          {seg.hanzi}
                          <rt style={{ fontSize: '0.55em', color: '#555' }}>{seg.pinyin}</rt>
                        </ruby>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Secondary: raw OCR details */}
            {ocrSegments.length > 0 && (
              <details style={{ marginTop: '1rem' }}>
                <summary>Extracted Text (OCR details)</summary>
                <ul>
                  {ocrSegments.map((segment, index) => (
                    <li key={`${segment.text}-${index}`}>
                      <span>{segment.text}</span>{' '}
                      <span>({segment.language}, {formatConfidence(segment.confidence)})</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

