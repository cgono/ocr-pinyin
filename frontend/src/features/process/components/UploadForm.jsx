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

function statusPanelClass(mutation) {
  if (mutation.isPending) return 'status-panel status-panel--loading'
  if (mutation.error) return 'status-panel status-panel--error'
  if (mutation.data?.status === 'partial') return 'status-panel status-panel--partial'
  if (mutation.data) return 'status-panel status-panel--success'
  return 'status-panel status-panel--idle'
}

function renderPinyinAnnotation(segment) {
  if (segment.alignment_status === 'uncertain') {
    return segment.reason_code === 'pinyin_execution_failed' ? 'Uncertain pronunciation' : 'Uncertain'
  }

  return segment.pinyin_text
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
        <div className="upload-actions">
          <button
            type="button"
            className="btn-primary"
            onClick={() => cameraInputRef.current?.click()}
          >
            Take Photo
          </button>
          <div className="file-input-wrapper">
            <label className="upload-label" htmlFor="upload-image">Upload image</label>
            <input
              id="upload-image"
              name="upload-image"
              type="file"
              accept="image/*"
              className="file-input"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </div>
          <button type="submit" disabled={mutation.isPending} className="btn-secondary">
            {mutation.isPending ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </form>

      <div className={statusPanelClass(mutation)}>
        <h2 className="status-panel__title">Processing Status</h2>
        {!mutation.data && !mutation.error && !mutation.isPending && (
          <p className="status-panel__message">Waiting for submission.</p>
        )}
        {mutation.isPending && (
          <p className="status-panel__message">Uploading image...</p>
        )}
        {mutation.error && (
          <p role="alert" className="status-panel__alert">
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
            {mutation.data.status === 'partial' && (
              <p className="status-panel__partial-note" aria-label="processing-partial">
                Partial result available
              </p>
            )}
            {mutation.data.status === 'partial' && mutation.data.warnings?.length > 0 && (
              <div aria-label="processing-warnings">
                {mutation.data.warnings.map((w, i) => (
                  <p
                    key={`${w.code}-${i}`}
                    className="status-panel__warning"
                    role="status"
                  >
                    {recoveryGuidanceByCode[w.code] || w.message}
                  </p>
                ))}
              </div>
            )}
            <p className="status-panel__meta">Status: {mutation.data.status}</p>
            <p className="status-panel__meta">Request ID: {mutation.data.request_id}</p>

            {/* Unified result: image + pinyin reading together */}
            {(previewUrl || pinyinSegments.length > 0) && (
              <div aria-label="result-view" className="result-view">
                {previewUrl && (
                  <div>
                    <img
                      src={previewUrl}
                      alt="Uploaded image"
                      className="result-image"
                    />
                  </div>
                )}

                {pinyinSegments.length > 0 && (
                  <div aria-label="pinyin-result">
                    <h3 className="pinyin-result__title">Pinyin Reading</h3>
                    <div className="pinyin-result__content">
                      {pinyinSegments.map((seg, index) => (
                        <ruby key={`${seg.source_text}-${seg.alignment_status}-${index}`}>
                          {seg.source_text}
                          <rt>{renderPinyinAnnotation(seg)}</rt>
                        </ruby>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Secondary: raw OCR details */}
            {ocrSegments.length > 0 && (
              <details className="details-section">
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
