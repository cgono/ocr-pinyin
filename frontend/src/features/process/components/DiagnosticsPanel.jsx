function formatConfidence(confidence) {
  return `${Math.round(confidence * 100)}%`
}

function formatMilliseconds(value) {
  return `${value.toFixed(1)}ms`
}

export default function DiagnosticsPanel({ diagnostics, ocrSegments = [] }) {
  if (!diagnostics && ocrSegments.length === 0) {
    return null
  }

  return (
    <details className="details-section" aria-label="diagnostics-panel">
      <summary>Show Details</summary>

      {ocrSegments.length > 0 && (
        <div>
          <h4>OCR Details</h4>
          <ul>
            {ocrSegments.map((segment, index) => (
              <li key={`${segment.text}-${index}`}>
                <span>{segment.text}</span>{' '}
                <span>({segment.language}, {formatConfidence(segment.confidence)})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {diagnostics && (
        <>
          <div>
            <h4>Timing</h4>
            <ul>
              <li>Total: {formatMilliseconds(diagnostics.timing.total_ms)}</li>
              <li>OCR: {formatMilliseconds(diagnostics.timing.ocr_ms)}</li>
              <li>Pinyin: {formatMilliseconds(diagnostics.timing.pinyin_ms)}</li>
            </ul>
          </div>

          <div>
            <h4>Trace</h4>
            <ul>
              {diagnostics.trace.steps.map((step, index) => (
                <li key={`${step.step}-${index}`}>{step.step}: {step.status}</li>
              ))}
            </ul>
          </div>
        </>
      )}
    </details>
  )
}
