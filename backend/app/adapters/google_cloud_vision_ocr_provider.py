"""Google Cloud Vision OCR provider.

LangChain is used for the extraction chain that transforms the raw GCV API
response (full_text_annotation) into normalised RawOcrSegment values.  The
chain is composed of two RunnableLambda steps:

  1. _gcv_response_to_documents – iterates TEXT blocks at paragraph granularity,
     extracts text by joining symbols, and wraps each paragraph in a LangChain
     Document carrying confidence and language metadata.
  2. _documents_to_segments – maps LangChain Documents to the adapter's
     RawOcrSegment dataclass.

Environment variables
---------------------
OCR_PROVIDER=google_vision              Activates this provider.
GOOGLE_APPLICATION_CREDENTIALS_JSON    GCP service account JSON embedded as a string value.
GOOGLE_CLOUD_PROJECT                   Optional; only needed if not encoded in the credentials.
"""

from __future__ import annotations

import json
import logging
import os

import google.api_core.exceptions
from google.cloud import vision
from google.oauth2 import service_account
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.adapters.ocr_provider import OcrExecutionError, ProviderUnavailableError, RawOcrSegment

logger = logging.getLogger(__name__)


def _paragraph_text(paragraph) -> str:
    """Join all symbols in a paragraph without separators (correct for Chinese)."""
    return "".join(
        "".join(symbol.text for symbol in word.symbols)
        for word in paragraph.words
    )


def _gcv_response_to_documents(response) -> list[Document]:
    """Iterate TEXT blocks at paragraph granularity and wrap each in a LangChain Document."""
    docs = []
    for page in response.full_text_annotation.pages or []:
        for block in page.blocks:
            if block.block_type != vision.Block.BlockType.TEXT:
                continue
            for paragraph in block.paragraphs:
                text = _paragraph_text(paragraph)
                if not text.strip():
                    continue
                langs = list(paragraph.property.detected_languages)
                language = langs[0].language_code if langs else None
                docs.append(
                    Document(
                        page_content=text,
                        metadata={"confidence": paragraph.confidence, "language": language},
                    )
                )
    return docs


def _documents_to_segments(docs: list[Document]) -> list[RawOcrSegment]:
    """Map LangChain Documents to OCR adapter segments."""
    return [
        RawOcrSegment(
            text=doc.page_content,
            language=doc.metadata.get("language"),
            confidence=doc.metadata["confidence"],
        )
        for doc in docs
    ]


# Module-level chain: GCV response → list[RawOcrSegment].
_extraction_chain = (
    RunnableLambda(_gcv_response_to_documents)
    | RunnableLambda(_documents_to_segments)
)


class GoogleCloudVisionOcrProvider:
    """Google Cloud Vision implementation of the OcrProvider protocol.

    Reads image bytes via GCV's DOCUMENT_TEXT_DETECTION API, then runs the
    result through the LangChain extraction chain to produce normalised
    RawOcrSegment values with per-paragraph language codes (e.g. "zh-Hans").
    """

    def __init__(self) -> None:
        try:
            creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
            if creds_json:
                normalized_creds_json = creds_json.strip()
                first, last = normalized_creds_json[:1], normalized_creds_json[-1:]
                if first == last and first in {"'", '"'}:
                    normalized_creds_json = normalized_creds_json[1:-1]
                info = json.loads(normalized_creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                self._client = vision.ImageAnnotatorClient(credentials=credentials)
            else:
                self._client = vision.ImageAnnotatorClient()
        except Exception as exc:
            raise ProviderUnavailableError(
                "Could not initialise Google Cloud Vision client. "
                "Check GOOGLE_APPLICATION_CREDENTIALS_JSON."
            ) from exc

    def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
        """Call GCV DOCUMENT_TEXT_DETECTION and return normalised segments via the chain."""
        try:
            response = self._client.document_text_detection(
                image=vision.Image(content=image_bytes)
            )
        except google.api_core.exceptions.GoogleAPIError as exc:
            raise OcrExecutionError(f"GCV API error: {exc}") from exc
        except Exception as exc:
            raise OcrExecutionError(f"Unexpected GCV error: {exc}") from exc

        paragraphs = sum(
            len(block.paragraphs)
            for page in (response.full_text_annotation.pages or [])
            for block in page.blocks
        )
        logger.debug("GCV returned %d paragraph(s)", paragraphs)
        logger.debug(
            "GCV first paragraph: %s",
            _paragraph_text(
                response.full_text_annotation.pages[0].blocks[0].paragraphs[0]
            )[:40]
            if paragraphs > 0
            else "(none)",
        )
        return _extraction_chain.invoke(response)
