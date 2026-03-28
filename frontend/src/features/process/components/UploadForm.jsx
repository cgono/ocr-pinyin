import { useEffect, useRef, useState } from 'react'

import { useMutation } from '@tanstack/react-query'

import { submitProcessRequest } from '../../../lib/api-client'
import CropPreview from './CropPreview'
import DiagnosticsPanel from './DiagnosticsPanel'

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
  ocr_low_confidence: 'OCR confidence is low. Tap Retake Photo for a clearer result.',
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
  const [cropImageUrl, setCropImageUrl] = useState(null)
  const [cameraFile, setCameraFile] = useState(null)
  const cameraInputRef = useRef(null)
  const [dismissedLowConfidence, setDismissedLowConfidence] = useState(false)

  // Create and revoke object URL when file changes
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    // URL.createObjectURL always returns a blob: URL; validate scheme before use
    if (!url.startsWith('blob:')) return
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const mutation = useMutation({
    mutationFn: (nextFile = file) => submitProcessRequest(nextFile),
  })

  const handleFileChange = (event) => {
    const nextFile = event.target.files?.[0] || null
    setFile(nextFile)
    setDismissedLowConfidence(false)
  }

  const handleCameraCapture = (event) => {
    const nextFile = event.target.files?.[0] || null
    event.target.value = ''

    if (!nextFile) {
      return
    }

    setCameraFile(nextFile)
    setCropImageUrl(URL.createObjectURL(nextFile))
    setDismissedLowConfidence(false)
    mutation.reset()
  }

  const handleCropConfirm = (croppedBlob) => {
    const nextFile = croppedBlob
      ? new globalThis.File([croppedBlob], cameraFile?.name || 'camera-capture.jpg', {
          type: croppedBlob.type || cameraFile?.type || 'image/jpeg',
        })
      : cameraFile

    setCropImageUrl(null)
    setFile(nextFile)
    setCameraFile(nextFile)
    setDismissedLowConfidence(false)
    mutation.mutate(nextFile)
  }

  const handleCropDismiss = () => {
    setCropImageUrl(null)
    setCameraFile(null)
    setFile(null)
    setPreviewUrl(null)
    setDismissedLowConfidence(false)
    mutation.reset()
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    setDismissedLowConfidence(false)
    mutation.mutate()
  }

  const pinyinSegments = mutation.data?.data?.pinyin?.segments || []
  const ocrSegments = mutation.data?.data?.ocr?.segments || []
  const isLowConfidence = mutation.data?.warnings?.some(w => w.code === 'ocr_low_confidence') ?? false

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
        onChange={handleCameraCapture}
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
              onChange={handleFileChange}
            />
          </div>
          <button type="submit" disabled={mutation.isPending || !!cropImageUrl} className="btn-secondary">
            {mutation.isPending ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </form>

      {cropImageUrl ? (
        <div className="status-panel status-panel--idle">
          <CropPreview
            imageUrl={cropImageUrl}
            onConfirm={handleCropConfirm}
            onDismiss={handleCropDismiss}
            disabled={mutation.isPending}
          />
        </div>
      ) : (
        <div className={statusPanelClass(mutation)}>
          <h2 className="status-panel__title">Processing Status</h2>
          {!mutation.data && !mutation.error && !mutation.isPending && (
            <p className="status-panel__message">Waiting for submission.</p>
          )}
          {mutation.isPending && (
            <p className="status-panel__message">
              <span className="loading-spinner" aria-hidden="true" />
              Uploading image...
            </p>
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
                  {mutation.data.warnings
                    .filter(w => w.code !== 'ocr_low_confidence')
                    .map((w, i) => (
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
              {isLowConfidence && !dismissedLowConfidence && (
                <div className="confidence-guidance" aria-label="low-confidence-guidance">
                  <p className="status-panel__warning">
                    {recoveryGuidanceByCode['ocr_low_confidence']}
                  </p>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => cameraInputRef.current?.click()}
                  >
                    Retake Photo
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setDismissedLowConfidence(true)}
                  >
                    Use This Result Anyway
                  </button>
                </div>
              )}
              <p className="status-panel__meta">Status: {mutation.data.status}</p>
              <p className="status-panel__meta">Request ID: {mutation.data.request_id}</p>

              {(previewUrl || pinyinSegments.length > 0) && (
                <div aria-label="result-view" className="result-view">
                  {previewUrl && (
                    <div>
                      <img
                        src={previewUrl} // codeql[js/xss-through-dom] - always a blob: URL from URL.createObjectURL
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

              <DiagnosticsPanel diagnostics={mutation.data?.diagnostics} ocrSegments={ocrSegments} />
            </div>
          )}
        </div>
      )}
    </section>
  )
}
