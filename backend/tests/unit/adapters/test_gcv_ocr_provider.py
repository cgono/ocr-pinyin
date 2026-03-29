"""Unit tests for the Google Cloud Vision OCR provider adapter.

Tests focus on the pure transformation functions (_gcv_response_to_documents,
_documents_to_segments) which can be exercised without GCP credentials.
"""

from types import SimpleNamespace

from google.cloud import vision

from app.adapters.google_cloud_vision_ocr_provider import (
    _documents_to_segments,
    _gcv_response_to_documents,
    _OcrDoc,
)


def _make_symbol(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text)


def _make_word(*chars: str) -> SimpleNamespace:
    return SimpleNamespace(symbols=[_make_symbol(c) for c in chars])


def _make_paragraph(
    chars: str,
    confidence: float = 0.9,
    language: str | None = "zh",
) -> SimpleNamespace:
    words = [_make_word(c) for c in chars]
    langs = [SimpleNamespace(language_code=language)] if language else []
    return SimpleNamespace(
        words=words,
        confidence=confidence,
        property=SimpleNamespace(detected_languages=langs),
    )


def _make_block(*paragraphs: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        block_type=vision.Block.BlockType.TEXT,
        paragraphs=list(paragraphs),
    )


def _make_response(*blocks: SimpleNamespace) -> SimpleNamespace:
    page = SimpleNamespace(blocks=list(blocks))
    return SimpleNamespace(
        full_text_annotation=SimpleNamespace(pages=[page])
    )


def test_gcv_response_assigns_sequential_line_ids_across_paragraphs() -> None:
    response = _make_response(
        _make_block(
            _make_paragraph("老师叫", confidence=0.95),
            _make_paragraph("同学们好", confidence=0.94),
        )
    )

    docs = _gcv_response_to_documents(response)

    assert len(docs) == 2
    assert docs[0].metadata["line_id"] == 0
    assert docs[1].metadata["line_id"] == 1


def test_gcv_response_line_ids_are_sequential_across_blocks() -> None:
    response = _make_response(
        _make_block(_make_paragraph("第一行")),
        _make_block(_make_paragraph("第二行")),
    )

    docs = _gcv_response_to_documents(response)

    assert docs[0].metadata["line_id"] == 0
    assert docs[1].metadata["line_id"] == 1


def test_gcv_response_skips_empty_paragraphs_without_incrementing_line_id() -> None:
    response = _make_response(
        _make_block(
            _make_paragraph("你好"),
            _make_paragraph("   "),   # whitespace-only, should be skipped
            _make_paragraph("世界"),
        )
    )

    docs = _gcv_response_to_documents(response)

    assert len(docs) == 2
    assert docs[0].metadata["line_id"] == 0
    assert docs[1].metadata["line_id"] == 1


def test_gcv_response_skips_non_text_blocks() -> None:
    non_text_block = SimpleNamespace(
        block_type=vision.Block.BlockType.BARCODE,
        paragraphs=[_make_paragraph("ignored")],
    )
    response = _make_response(
        non_text_block,
        _make_block(_make_paragraph("你好")),
    )

    docs = _gcv_response_to_documents(response)

    assert len(docs) == 1
    assert docs[0].metadata["line_id"] == 0


def test_documents_to_segments_maps_line_id() -> None:
    docs = [
        _OcrDoc(page_content="你好", metadata={"confidence": 0.9, "language": "zh", "line_id": 0}),
        _OcrDoc(page_content="世界", metadata={"confidence": 0.8, "language": "zh", "line_id": 1}),
    ]

    segments = _documents_to_segments(docs)

    assert segments[0].line_id == 0
    assert segments[1].line_id == 1


def test_documents_to_segments_handles_missing_line_id() -> None:
    docs = [
        _OcrDoc(page_content="你好", metadata={"confidence": 0.9, "language": "zh"}),
    ]

    segments = _documents_to_segments(docs)

    assert segments[0].line_id is None
