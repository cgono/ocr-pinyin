from typing import Literal

from pydantic import BaseModel, Field, model_validator


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


class CostEstimate(BaseModel):
    estimated_usd: float | None = Field(default=None, ge=0)
    estimated_sgd: float | None = Field(default=None, ge=0)
    confidence: Literal["full", "fallback", "unavailable"]

    @model_validator(mode="after")
    def full_confidence_requires_currency_values(self) -> "CostEstimate":
        if self.confidence == "full" and (
            self.estimated_usd is None or self.estimated_sgd is None
        ):
            msg = "estimated_usd and estimated_sgd are required when confidence is 'full'"
            raise ValueError(msg)
        return self


class DiagnosticsPayload(BaseModel):
    upload_context: UploadContext
    timing: TimingInfo
    trace: TraceInfo
    cost_estimate: CostEstimate | None = None
