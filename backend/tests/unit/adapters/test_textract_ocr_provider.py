"""Unit tests for the AWS Textract OCR provider adapter.

All Textract API calls are mocked via unittest.mock so these tests run without
AWS credentials or network access.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.ocr_provider import OcrExecutionError
from app.adapters.textract_ocr_provider import TextractOcrProvider

_TEXTRACT_TWO_LINE_RESPONSE = {
    "Blocks": [
        {"BlockType": "LINE", "Text": "你好", "Confidence": 92.0},
        {"BlockType": "LINE", "Text": "hello", "Confidence": 80.0},
        # WORD blocks must be excluded from output
        {"BlockType": "WORD", "Text": "你好", "Confidence": 91.0},
    ]
}


def _make_provider(response: dict) -> TextractOcrProvider:
    """Return a TextractOcrProvider whose boto3 client is stubbed with *response*."""
    with patch("app.adapters.textract_ocr_provider.boto3.client") as mock_factory:
        mock_client = MagicMock()
        mock_client.detect_document_text.return_value = response
        mock_factory.return_value = mock_client
        provider = TextractOcrProvider(region_name="us-east-1")
        provider._client = mock_client  # keep stub active outside the patch context
    return provider


def test_extract_returns_line_level_segments_only() -> None:
    provider = _make_provider(_TEXTRACT_TWO_LINE_RESPONSE)

    segments = provider.extract(image_bytes=b"fake-image", content_type="image/png")

    # Only LINE blocks → 2 segments; WORD block is excluded.
    assert len(segments) == 2
    assert segments[0].text == "你好"
    assert segments[0].confidence == 92.0
    assert segments[0].language is None  # Textract does not return language tags


def test_extract_maps_confidence_from_textract_float() -> None:
    provider = _make_provider(
        {"Blocks": [{"BlockType": "LINE", "Text": "世界", "Confidence": 99.5}]}
    )

    segments = provider.extract(image_bytes=b"fake-image", content_type="image/jpeg")

    assert segments[0].confidence == 99.5


def test_extract_excludes_blocks_with_no_text() -> None:
    provider = _make_provider(
        {
            "Blocks": [
                {"BlockType": "LINE", "Text": "", "Confidence": 90.0},
                {"BlockType": "LINE", "Confidence": 85.0},  # no "Text" key
                {"BlockType": "PAGE", "Confidence": 99.0},
            ]
        }
    )

    segments = provider.extract(image_bytes=b"fake-image", content_type="image/png")

    assert segments == []


def test_extract_returns_empty_list_for_empty_blocks() -> None:
    provider = _make_provider({"Blocks": []})

    segments = provider.extract(image_bytes=b"fake-image", content_type="image/png")

    assert segments == []


def test_extract_raises_ocr_execution_error_on_client_error() -> None:
    from botocore.exceptions import ClientError

    provider = _make_provider({})
    provider._client.detect_document_text.side_effect = ClientError(
        {"Error": {"Code": "InvalidDocumentException", "Message": "Invalid document"}},
        "DetectDocumentText",
    )

    with pytest.raises(OcrExecutionError):
        provider.extract(image_bytes=b"bad-image", content_type="image/png")


def test_extract_raises_ocr_execution_error_on_unexpected_exception() -> None:
    provider = _make_provider({})
    provider._client.detect_document_text.side_effect = RuntimeError("network blip")

    with pytest.raises(OcrExecutionError):
        provider.extract(image_bytes=b"bad-image", content_type="image/png")


def test_langchain_chain_invoked_with_full_response() -> None:
    """Verify the provider passes the full Textract response dict (not just Blocks) to the chain."""
    provider = _make_provider(_TEXTRACT_TWO_LINE_RESPONSE)

    with patch("app.adapters.textract_ocr_provider._extraction_chain") as mock_chain:
        mock_chain.invoke.return_value = []
        provider.extract(image_bytes=b"fake", content_type="image/png")

    mock_chain.invoke.assert_called_once_with(_TEXTRACT_TWO_LINE_RESPONSE)
