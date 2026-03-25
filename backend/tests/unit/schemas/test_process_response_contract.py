import pytest
from pydantic import ValidationError

from app.schemas.diagnostics import DiagnosticsPayload, TimingInfo, TraceInfo, UploadContext
from app.schemas.process import (
    OcrData,
    OcrSegment,
    ProcessData,
    ProcessError,
    ProcessResponse,
    ProcessWarning,
)


def _minimal_diagnostics() -> DiagnosticsPayload:
    return DiagnosticsPayload(
        upload_context=UploadContext(content_type="image/png", file_size_bytes=1),
        timing=TimingInfo(total_ms=0.0, ocr_ms=0.0, pinyin_ms=0.0),
        trace=TraceInfo(steps=[]),
    )


def test_success_envelope_requires_data() -> None:
    response = ProcessResponse(
        status="success",
        request_id="req-1",
        data=ProcessData(
            ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.88)])
        ),
        diagnostics=_minimal_diagnostics(),
    )
    assert response.data is not None
    assert response.error is None
    assert response.warnings is None


def test_partial_envelope_requires_data_and_warnings() -> None:
    response = ProcessResponse(
        status="partial",
        request_id="req-2",
        data=ProcessData(
            ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.51)])
        ),
        warnings=[
            ProcessWarning(category="ocr", code="ocr-low-confidence", message="Low confidence")
        ],
        diagnostics=_minimal_diagnostics(),
    )
    assert response.data is not None
    assert response.warnings is not None
    assert response.error is None


def test_error_envelope_requires_error() -> None:
    response = ProcessResponse(
        status="error",
        request_id="req-3",
        error=ProcessError(code="invalid-image", message="Unsupported file"),
    )
    assert response.error is not None
    assert response.data is None
    assert response.warnings is None


def test_success_envelope_rejects_error_field() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="success",
            request_id="req-4",
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.6)]),
            ),
            diagnostics=_minimal_diagnostics(),
            error=ProcessError(code="bad", message="should not exist"),
        )


def test_success_envelope_rejects_warnings_field() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="success",
            request_id="req-5",
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.5)])
            ),
            diagnostics=_minimal_diagnostics(),
            warnings=[ProcessWarning(category="ocr", code="warn", message="should not exist")],
        )


def test_partial_envelope_rejects_error_field() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="partial",
            request_id="req-6",
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.7)])
            ),
            diagnostics=_minimal_diagnostics(),
            warnings=[ProcessWarning(category="ocr", code="low-conf", message="ok")],
            error=ProcessError(code="bad", message="should not exist"),
        )


def test_partial_envelope_requires_warnings() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="partial",
            request_id="req-7",
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.9)])
            ),
            diagnostics=_minimal_diagnostics(),
            # warnings omitted — must fail
        )


def test_error_envelope_rejects_data_field() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="error",
            request_id="req-8",
            error=ProcessError(code="fail", message="error"),
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.8)])
            ),
        )


def test_error_envelope_rejects_warnings_field() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="error",
            request_id="req-9",
            error=ProcessError(code="fail", message="error"),
            warnings=[ProcessWarning(category="system", code="warn", message="should not be here")],
        )


def test_partial_envelope_rejects_invalid_warning_category() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="partial",
            request_id="req-10",
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.9)])
            ),
            diagnostics=_minimal_diagnostics(),
            warnings=[ProcessWarning(category="processing", code="warn", message="bad taxonomy")],
        )


def test_success_envelope_requires_diagnostics() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="success",
            request_id="req-11",
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.88)])
            ),
        )


def test_partial_envelope_requires_diagnostics() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="partial",
            request_id="req-12",
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.51)])
            ),
            warnings=[
                ProcessWarning(category="ocr", code="ocr-low-confidence", message="Low confidence")
            ],
        )


def test_error_envelope_rejects_diagnostics() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="error",
            request_id="req-13",
            error=ProcessError(code="invalid-image", message="Unsupported file"),
            diagnostics=_minimal_diagnostics(),
        )
