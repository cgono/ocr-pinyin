import { useEffect, useRef, useState } from 'react'

import ReactCrop from 'react-image-crop'
import 'react-image-crop/dist/ReactCrop.css'

async function cropToBlob(imageElement, completedCrop, mimeType = 'image/jpeg') {
  const scaleX = imageElement.naturalWidth / imageElement.width
  const scaleY = imageElement.naturalHeight / imageElement.height
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(completedCrop.width * scaleX))
  canvas.height = Math.max(1, Math.round(completedCrop.height * scaleY))

  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('Canvas context unavailable')
  }

  context.drawImage(
    imageElement,
    completedCrop.x * scaleX,
    completedCrop.y * scaleY,
    completedCrop.width * scaleX,
    completedCrop.height * scaleY,
    0,
    0,
    canvas.width,
    canvas.height
  )

  return await new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob)
        return
      }
      reject(new Error('Failed to create cropped image'))
    }, mimeType, 0.9)
  })
}

export default function CropPreview({ imageUrl, onConfirm, onDismiss, disabled = false }) {
  const imageRef = useRef(null)
  const [crop, setCrop] = useState()
  const [completedCrop, setCompletedCrop] = useState()

  useEffect(() => () => {
    URL.revokeObjectURL(imageUrl)
  }, [imageUrl])

  // P4: reset crop selection when a new image URL is loaded (e.g. second camera capture)
  useEffect(() => {
    setCrop(undefined)
    setCompletedCrop(undefined)
  }, [imageUrl])

  const handleConfirm = async () => {
    if (!imageRef.current) {
      return
    }

    // P3: image not yet loaded — treat as full-image (no crop)
    if (!imageRef.current.naturalWidth || !imageRef.current.naturalHeight) {
      onConfirm()
      return
    }

    if (!completedCrop?.width || !completedCrop?.height) {
      onConfirm()
      return
    }

    // P1: surface cropToBlob failures rather than silently freezing
    try {
      const blob = await cropToBlob(imageRef.current, completedCrop)
      onConfirm(blob)
    } catch {
      onDismiss()
    }
  }

  return (
    <section className="crop-preview" aria-label="crop-preview">
      <h2 className="status-panel__title">Preview and Crop</h2>
      <p className="status-panel__message">
        Adjust the frame if needed, then confirm to submit the photo.
      </p>

      <ReactCrop crop={crop} onChange={setCrop} onComplete={setCompletedCrop}>
        <img
          ref={imageRef}
          src={imageUrl} // codeql[js/xss-through-dom] - always a blob: URL from URL.createObjectURL
          alt="Captured photo preview"
          className="crop-preview__image"
        />
      </ReactCrop>

      <div className="crop-preview__actions">
        <button type="button" className="btn-primary" onClick={handleConfirm} disabled={disabled}>
          Confirm
        </button>
        <button type="button" className="btn-secondary" onClick={onDismiss} disabled={disabled}>
          Cancel
        </button>
      </div>
    </section>
  )
}
