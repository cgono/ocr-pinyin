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

function groupSegmentsByLine(segments) {
  const hasLineIds = segments.some(seg => seg.line_id != null)
  if (!hasLineIds) return null

  const groups = []
  let currentLineId
  let currentGroup = []

  for (const seg of segments) {
    if (seg.line_id !== currentLineId && currentGroup.length > 0) {
      groups.push({ line_id: currentLineId, segments: currentGroup })
      currentGroup = []
    }

    currentLineId = seg.line_id
    currentGroup.push(seg)
  }

  if (currentGroup.length > 0) {
    groups.push({ line_id: currentLineId, segments: currentGroup })
  }

  return groups
}

function buildDisplayParts(displayText, segments) {
  if (!displayText) return null

  const parts = []
  let cursor = 0

  for (const segment of segments) {
    const nextIndex = displayText.indexOf(segment.source_text, cursor)
    if (nextIndex < 0) {
      return null
    }

    parts.push({
      prefixText: displayText.slice(cursor, nextIndex),
      segment,
    })
    cursor = nextIndex + segment.source_text.length
  }

  return {
    parts,
    suffixText: displayText.slice(cursor),
  }
}

function resolveDerivedReadingGroups(reading, pinyinSegments) {
  if (!reading?.provider?.applied || !Array.isArray(reading.groups) || reading.groups.length === 0) {
    return null
  }

  const resolvedGroups = []

  for (const group of reading.groups) {
    if (!Array.isArray(group.segment_indexes) || group.segment_indexes.length === 0) {
      return null
    }

    const segments = group.segment_indexes.map((segmentIndex) => pinyinSegments[segmentIndex])
    if (segments.some(segment => !segment)) {
      return null
    }

    for (let index = 1; index < group.segment_indexes.length; index += 1) {
      if (group.segment_indexes[index] !== group.segment_indexes[index - 1] + 1) {
        return null
      }
    }

    const lineId = segments[0].line_id
    if (lineId == null || segments.some(segment => segment.line_id !== lineId)) {
      return null
    }

    if (group.line_id !== lineId) {
      return null
    }

    const displayParts = buildDisplayParts(group.display_text, segments)
    if (!displayParts) {
      return null
    }

    resolvedGroups.push({
      group_id: group.group_id,
      line_id: lineId,
      segments,
      displayParts,
      playbackText: group.playback_text || group.display_text,
      labelText: group.playback_text || group.display_text,
      translationText: segments.find(segment => segment.translation_text)?.translation_text ?? null,
    })
  }

  return resolvedGroups
}

function buildFallbackRenderParts(segments) {
  return {
    parts: segments.map(segment => ({
      prefixText: '',
      segment,
    })),
    suffixText: '',
  }
}

function normalizeFallbackGroups(lineGroups) {
  if (!lineGroups?.length) {
    return null
  }

  return lineGroups.map((group, groupIndex) => ({
    group_id: `fallback-${group.line_id ?? 'line'}-${groupIndex}`,
    line_id: group.line_id,
    segments: group.segments,
    displayParts: buildFallbackRenderParts(group.segments),
    playbackText: buildSpokenLineText(group),
    labelText: buildSpokenLineText(group),
    translationText: group.segments.find(segment => segment.translation_text)?.translation_text ?? null,
  }))
}

function selectChineseVoice(voices) {
  return voices.find((voice) => /^zh\b/i.test(voice.lang) || /^cmn\b/i.test(voice.lang)) ?? null
}

function buildSpokenLineText(group) {
  return group.segments.map((segment) => segment.source_text).join('')
}

export default function UploadForm() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [cropImageUrl, setCropImageUrl] = useState(null)
  const [cameraFile, setCameraFile] = useState(null)
  const cameraInputRef = useRef(null)
  const [dismissedLowConfidence, setDismissedLowConfidence] = useState(false)
  const [selectedVoice, setSelectedVoice] = useState(null)
  const [speechFallbackMessage, setSpeechFallbackMessage] = useState(null)
  const [activeLineKey, setActiveLineKey] = useState(null)
  const [isPagePlaybackActive, setIsPagePlaybackActive] = useState(false)
  const activeLineKeyRef = useRef(null)
  const activeUtteranceRef = useRef(null)
  const activePlaybackModeRef = useRef(null)
  const playbackSessionRef = useRef(0)
  const queuedPagePlaybackTimeoutRef = useRef(null)
  const ignoreNextSpeechErrorRef = useRef(false)
  const cancelPlaybackIfActiveRef = useRef(() => {})

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
  const readingData = mutation.data?.data?.reading || null
  const isLowConfidence = mutation.data?.warnings?.some(w => w.code === 'ocr_low_confidence') ?? false
  const lineGroups = groupSegmentsByLine(pinyinSegments)
  const derivedReadingGroups = resolveDerivedReadingGroups(readingData, pinyinSegments)
  const playbackGroups = derivedReadingGroups ?? normalizeFallbackGroups(lineGroups)
  const hasPlaybackGroups = (playbackGroups?.length ?? 0) > 0

  function clearActivePlayback() {
    if (queuedPagePlaybackTimeoutRef.current != null) {
      globalThis.clearTimeout(queuedPagePlaybackTimeoutRef.current)
      queuedPagePlaybackTimeoutRef.current = null
    }

    activeLineKeyRef.current = null
    activeUtteranceRef.current = null
    activePlaybackModeRef.current = null
    playbackSessionRef.current += 1
    setActiveLineKey(null)
    setIsPagePlaybackActive(false)
  }

  function cancelPlayback() {
    const speechSynthesis = globalThis.window?.speechSynthesis

    ignoreNextSpeechErrorRef.current = true
    clearActivePlayback()
    speechSynthesis?.cancel?.()
  }

  cancelPlaybackIfActiveRef.current = () => {
    if (!activeUtteranceRef.current && activeLineKeyRef.current == null) {
      return
    }

    cancelPlayback()
  }

  useEffect(() => {
    if (
      typeof globalThis.window === 'undefined' ||
      !globalThis.window.speechSynthesis ||
      typeof globalThis.SpeechSynthesisUtterance !== 'function'
    ) {
      setSelectedVoice(null)
      setSpeechFallbackMessage('Pronunciation playback is not supported in this browser.')
      return undefined
    }

    const speechSynthesis = globalThis.window.speechSynthesis
    const updateVoiceSelection = () => {
      const nextVoice = selectChineseVoice(speechSynthesis.getVoices())

      setSelectedVoice(nextVoice)
      setSpeechFallbackMessage(
        nextVoice ? null : 'Pronunciation playback is unavailable because no Chinese voice is available.'
      )
    }

    updateVoiceSelection()
    speechSynthesis.addEventListener?.('voiceschanged', updateVoiceSelection)

    return () => {
      speechSynthesis.removeEventListener?.('voiceschanged', updateVoiceSelection)
      cancelPlaybackIfActiveRef.current()
    }
  }, [])

  useEffect(() => {
    setSpeechFallbackMessage((currentMessage) => (
      currentMessage === 'Pronunciation playback is unavailable right now.'
        ? null
        : currentMessage
    ))
    cancelPlaybackIfActiveRef.current()
  }, [mutation.data?.request_id])

  function startUtterance({
    lineText,
    lineKey,
    mode,
    onSequenceEnd,
  }) {
    const speechSynthesis = globalThis.window?.speechSynthesis

    if (!speechSynthesis || !selectedVoice || !lineText) {
      return
    }

    const sessionId = playbackSessionRef.current + 1
    playbackSessionRef.current = sessionId

    try {
      const utterance = new globalThis.SpeechSynthesisUtterance(lineText)
      utterance.voice = selectedVoice
      utterance.lang = selectedVoice.lang || 'zh-CN'
      utterance.onend = () => {
        if (playbackSessionRef.current !== sessionId || activeLineKeyRef.current !== lineKey) {
          ignoreNextSpeechErrorRef.current = false
          return
        }

        if (mode === 'page' && typeof onSequenceEnd === 'function') {
          onSequenceEnd()
        } else {
          clearActivePlayback()
        }

        ignoreNextSpeechErrorRef.current = false
      }
      utterance.onerror = (event) => {
        const isExpectedCancel =
          ignoreNextSpeechErrorRef.current ||
          event?.error === 'canceled' ||
          event?.error === 'interrupted'

        if (playbackSessionRef.current === sessionId && activeLineKeyRef.current === lineKey) {
          clearActivePlayback()
        }

        if (!isExpectedCancel) {
          setSpeechFallbackMessage('Pronunciation playback is unavailable right now.')
        }

        ignoreNextSpeechErrorRef.current = false
      }

      activePlaybackModeRef.current = mode
      activeLineKeyRef.current = lineKey
      activeUtteranceRef.current = utterance
      setActiveLineKey(lineKey)
      setIsPagePlaybackActive(mode === 'page')
      ignoreNextSpeechErrorRef.current = false
      speechSynthesis.speak(utterance)
    } catch {
      clearActivePlayback()
      setSpeechFallbackMessage('Pronunciation playback is unavailable right now.')
    }
  }

  function startPagePlayback(groupIndex = 0) {
    if (!hasPlaybackGroups || !playbackGroups?.[groupIndex]) {
      clearActivePlayback()
      return
    }

    const group = playbackGroups[groupIndex]
    const lineText = group.playbackText
    const lineKey = group.group_id

    startUtterance({
      lineText,
      lineKey,
      mode: 'page',
      onSequenceEnd: () => {
        const nextIndex = groupIndex + 1

        if (!playbackGroups?.[nextIndex]) {
          clearActivePlayback()
          return
        }

        queuedPagePlaybackTimeoutRef.current = globalThis.setTimeout(() => {
          queuedPagePlaybackTimeoutRef.current = null
          startPagePlayback(nextIndex)
        }, 0)
      },
    })
  }

  const handleLinePlayback = (group) => {
    const lineText = group.playbackText
    const lineKey = group.group_id

    if (!selectedVoice || !lineText) {
      return
    }

    if (activePlaybackModeRef.current === 'line' && activeLineKeyRef.current === lineKey) {
      cancelPlayback()
      return
    }

    cancelPlayback()
    startUtterance({
      lineText,
      lineKey,
      mode: 'line',
    })
  }

  const handlePagePlayback = () => {
    if (!selectedVoice || !hasPlaybackGroups) {
      return
    }

    if (activePlaybackModeRef.current === 'page') {
      cancelPlayback()
      return
    }

    cancelPlayback()
    startPagePlayback()
  }

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
                      <div className="pinyin-result__header">
                        <h3 className="pinyin-result__title">Pinyin Reading</h3>
                        {hasPlaybackGroups && (
                          <button
                            type="button"
                            className="pinyin-playback-button pinyin-playback-button--page"
                            aria-label={
                              isPagePlaybackActive
                                ? 'Stop page pronunciation playback'
                                : 'Play page pronunciation playback'
                            }
                            aria-pressed={isPagePlaybackActive}
                            disabled={!!speechFallbackMessage || !selectedVoice}
                            onClick={handlePagePlayback}
                          >
                            {speechFallbackMessage || !selectedVoice
                              ? 'Unavailable'
                              : isPagePlaybackActive
                                ? 'Stop Page'
                                : 'Play Page'}
                          </button>
                        )}
                      </div>
                      {speechFallbackMessage && (
                        <p className="pinyin-playback-note" role="status">
                          {speechFallbackMessage}
                        </p>
                      )}
                      {derivedReadingGroups && readingData?.provider?.applied && (
                        <p className="pinyin-reading-note" role="status">
                          Auto-punctuation applied by {readingData.provider.name}.
                        </p>
                      )}
                      <div className="pinyin-result__content">
                        {hasPlaybackGroups ? playbackGroups.map((group, groupIndex) => {
                          const spokenLineText = group.labelText
                          const lineKey = group.group_id
                          const isPlaying = activeLineKey === lineKey
                          const isPlaybackDisabled = !!speechFallbackMessage || !selectedVoice || !spokenLineText
                          const buttonLabel = isPlaybackDisabled
                            ? `Pronunciation unavailable for ${spokenLineText}`
                            : `${isPlaying ? 'Stop' : 'Play'} pronunciation for ${spokenLineText}`

                          return (
                            <div
                              key={`line-${group.line_id}-${groupIndex}-${group.group_id}`}
                              className={`pinyin-line-group${isPlaying ? ' pinyin-line-group--active' : ''}`}
                            >
                              <div className="pinyin-line-group__header">
                                <div className="pinyin-line-group__ruby">
                                  {group.displayParts.parts.map(({ prefixText, segment }, segmentIndex) => (
                                    <span key={`${segment.source_text}-${segment.alignment_status}-${segmentIndex}`}>
                                      {prefixText && (
                                        <span className="pinyin-inline-punctuation">{prefixText}</span>
                                      )}
                                      <ruby>
                                        {segment.source_text}
                                        <rt>{renderPinyinAnnotation(segment)}</rt>
                                      </ruby>
                                    </span>
                                  ))}
                                  {group.displayParts.suffixText && (
                                    <span className="pinyin-inline-punctuation">{group.displayParts.suffixText}</span>
                                  )}
                                </div>
                                <button
                                  type="button"
                                  className="pinyin-playback-button"
                                  aria-label={buttonLabel}
                                  aria-pressed={isPlaying}
                                  disabled={isPlaybackDisabled}
                                  onClick={() => handleLinePlayback(group)}
                                >
                                  {isPlaybackDisabled ? 'Unavailable' : isPlaying ? 'Stop' : 'Play'}
                                </button>
                              </div>
                              {group.translationText && (
                                <p className="pinyin-line-translation">
                                  {group.translationText}
                                </p>
                              )}
                            </div>
                          )
                        }) : (
                          <div className="pinyin-result__flat">
                            <div className="pinyin-line-group__ruby">
                              {pinyinSegments.map((seg, segmentIndex) => (
                                <ruby key={`${seg.source_text}-${seg.alignment_status}-${segmentIndex}`}>
                                  {seg.source_text}
                                  <rt>{renderPinyinAnnotation(seg)}</rt>
                                </ruby>
                              ))}
                            </div>
                          </div>
                        )}
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
