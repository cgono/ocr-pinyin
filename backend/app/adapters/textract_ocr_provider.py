# LEGACY: Requires boto3. Does not support Chinese script. Use google_vision instead.
"""AWS Textract OCR provider.

LangChain is used for the extraction chain that transforms the raw Textract API
response (a list of Block dicts) into normalised RawOcrSegment values.  The
chain is composed of two RunnableLambda steps:

  1. _textract_response_to_documents – keeps only LINE-level blocks and wraps
     each one in a LangChain Document so later stages can be swapped in without
     touching the provider interface.
  2. _documents_to_segments – maps LangChain Documents to the adapter's
     RawOcrSegment dataclass, carrying text and confidence from Textract.
     Language is left as None because Textract's DetectDocumentText does not
     return a language tag; the OCR service layer normalises it to "und" and the
     CJK filter determines usability.

Environment variables
---------------------
OCR_PROVIDER=textract     Activates this provider (read by get_ocr_provider()).
AWS_REGION                AWS region for the Textract client (default: us-east-1).
AWS credentials           Standard boto3 resolution (env vars, ~/.aws, IAM role).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.adapters.ocr_provider import OcrExecutionError, ProviderUnavailableError, RawOcrSegment

logger = logging.getLogger(__name__)


def _textract_response_to_documents(response: dict[str, Any]) -> list[Document]:
    """Keep only LINE-level Textract blocks and wrap each in a LangChain Document."""
    blocks: list[dict[str, Any]] = response.get("Blocks", [])
    return [
        Document(
            page_content=block["Text"],
            metadata={"confidence": block.get("Confidence", 0.0)},
        )
        for block in blocks
        if block.get("BlockType") == "LINE" and block.get("Text")
    ]


def _documents_to_segments(docs: list[Document]) -> list[RawOcrSegment]:
    """Map LangChain Documents to OCR adapter segments."""
    return [
        RawOcrSegment(
            text=doc.page_content,
            language=None,  # Textract DetectDocumentText does not return language tags.
            confidence=doc.metadata["confidence"],
        )
        for doc in docs
    ]


# Module-level chain: Textract response dict → list[RawOcrSegment].
_extraction_chain = (
    RunnableLambda(_textract_response_to_documents)
    | RunnableLambda(_documents_to_segments)
)


class TextractOcrProvider:
    """AWS Textract implementation of the OcrProvider protocol.

    Reads image bytes via Textract's DetectDocumentText API, then runs the
    result through the LangChain extraction chain to produce normalised
    RawOcrSegment values.
    """

    def __init__(self, region_name: str | None = None) -> None:
        region = region_name or os.environ.get("AWS_REGION", "us-east-1")
        try:
            self._client = boto3.client("textract", region_name=region)
        except Exception as exc:  # boto3 setup errors (credentials shape, etc.)
            raise ProviderUnavailableError(
                "Could not initialise Textract client. Check AWS credentials and region."
            ) from exc

    def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
        """Call Textract and return normalised segments via the LangChain chain."""
        try:
            response = self._client.detect_document_text(Document={"Bytes": image_bytes})
        except (BotoCoreError, ClientError) as exc:
            raise OcrExecutionError(f"Textract API error: {exc}") from exc
        except Exception as exc:
            raise OcrExecutionError(f"Unexpected Textract error: {exc}") from exc

        blocks = response.get("Blocks", [])
        logger.debug(
            "Textract returned %d block(s): %s",
            len(blocks),
            [(b.get("BlockType"), b.get("Text", "")[:40]) for b in blocks],
        )
        return _extraction_chain.invoke(response)
