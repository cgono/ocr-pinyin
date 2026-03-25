from typing import Literal

from pydantic import BaseModel, Field


class UploadContext(BaseModel):
    content_type: str
    file_size_bytes: int = Field(..., ge=0)


class TimingInfo(BaseModel):
    total_ms: float = Field(..., ge=0)
    ocr_ms: float = Field(..., ge=0)
    pinyin_ms: float = Field(..., ge=0)


class TraceStep(BaseModel):
    step: Literal["ocr", "pinyin", "confidence_check"]
    status: Literal["ok", "skipped", "failed"]


class TraceInfo(BaseModel):
    steps: list[TraceStep]


class DiagnosticsPayload(BaseModel):
    upload_context: UploadContext
    timing: TimingInfo
    trace: TraceInfo
