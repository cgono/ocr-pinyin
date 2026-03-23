import pytest
from pydantic import ValidationError

from app.schemas.process import (
    OcrData,
    OcrSegment,
    ProcessData,
    ProcessError,
    ProcessResponse,
    ProcessWarning,
)


def test_success_envelope_requires_data() -> None:
    response = ProcessResponse(
        status="success",
        request_id="req-1",
        data=ProcessData(
            ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.88)])
        ),
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
        warnings=[ProcessWarning(code="ocr-low-confidence", message="Low confidence")],
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
            warnings=[ProcessWarning(code="warn", message="should not exist")],
        )


def test_partial_envelope_rejects_error_field() -> None:
    with pytest.raises(ValidationError):
        ProcessResponse(
            status="partial",
            request_id="req-6",
            data=ProcessData(
                ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.7)])
            ),
            warnings=[ProcessWarning(code="low-conf", message="ok")],
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
            warnings=[ProcessWarning(code="warn", message="should not be here")],
        )
