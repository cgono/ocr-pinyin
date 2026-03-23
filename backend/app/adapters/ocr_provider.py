from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RawOcrSegment:
    text: str
    language: str | None = None
    confidence: float | int | None = None


class OcrProvider(Protocol):
    def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
        """Extract raw OCR segments from image bytes."""


class ProviderUnavailableError(Exception):
    pass


class OcrExecutionError(Exception):
    pass


class NoOpOcrProvider:
    def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
        _ = (image_bytes, content_type)
        raise ProviderUnavailableError("OCR provider is not configured")


def get_ocr_provider() -> OcrProvider:
    """Return the active OCR provider based on the OCR_PROVIDER environment variable.

    Supported values:
      google_vision  – Google Cloud Vision DOCUMENT_TEXT_DETECTION (production)
      textract       – AWS Textract via LangChain extraction chain (legacy; no Chinese support)
      (unset)        – NoOpOcrProvider (raises ProviderUnavailableError on use)
    """
    import os

    provider = os.environ.get("OCR_PROVIDER", "").lower()
    if provider == "google_vision":
        from app.adapters.google_cloud_vision_ocr_provider import GoogleCloudVisionOcrProvider

        return GoogleCloudVisionOcrProvider()
    if provider == "textract":
        from app.adapters.textract_ocr_provider import TextractOcrProvider

        return TextractOcrProvider()
    return NoOpOcrProvider()
