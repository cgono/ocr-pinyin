from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.diagnostics import DiagnosticsPayload

ErrorCategory = Literal["validation", "ocr", "pinyin", "system", "budget", "upstream"]
ReadingProviderKind = Literal["heuristic", "remote_service", "llm"]


class OcrSegment(BaseModel):
    text: str
    language: str
    confidence: float = Field(ge=0.0, le=1.0)
    line_id: int | None = Field(default=None, ge=0)


class OcrData(BaseModel):
    segments: list[OcrSegment]


class PinyinSegment(BaseModel):
    source_text: str
    pinyin_text: str
    alignment_status: Literal["aligned", "uncertain"]
    reason_code: str | None = None
    line_id: int | None = None
    translation_text: str | None = None


class PinyinData(BaseModel):
    segments: list[PinyinSegment]


class ReadingProviderInfo(BaseModel):
    kind: ReadingProviderKind
    name: str
    version: str
    applied: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    request_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ReadingGroup(BaseModel):
    group_id: str
    line_id: int = Field(ge=0)
    raw_text: str
    display_text: str
    playback_text: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    segment_indexes: list[int] = Field(min_length=1)


class ReadingData(BaseModel):
    mode: Literal["derived"]
    provider: ReadingProviderInfo
    groups: list[ReadingGroup] = Field(default_factory=list)


class ProcessData(BaseModel):
    model_config = ConfigDict(extra="allow")

    ocr: OcrData | None = None
    pinyin: PinyinData | None = None
    reading: ReadingData | None = None
    message: str | None = None
    job_id: str | None = None


class ProcessWarning(BaseModel):
    category: ErrorCategory
    code: str
    message: str


class ProcessError(BaseModel):
    category: str = "processing"
    code: str
    message: str


class ProcessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "partial", "error"]
    request_id: str
    data: ProcessData | None = None
    warnings: list[ProcessWarning] | None = None
    error: ProcessError | None = None
    diagnostics: DiagnosticsPayload | None = None

    @model_validator(mode="after")
    def validate_status_envelope(self) -> "ProcessResponse":
        if self.status == "success":
            if self.data is None:
                raise ValueError("success responses require data")
            if self.diagnostics is None:
                raise ValueError("success responses require diagnostics")
            if self.warnings is not None or self.error is not None:
                raise ValueError("success responses cannot include warnings or error")
        elif self.status == "partial":
            if self.data is None or self.warnings is None:
                raise ValueError("partial responses require data and warnings")
            if self.diagnostics is None:
                raise ValueError("partial responses require diagnostics")
            if self.error is not None:
                raise ValueError("partial responses cannot include error")
        elif self.status == "error":
            if self.error is None:
                raise ValueError("error responses require error")
            if self.data is not None or self.warnings is not None:
                raise ValueError("error responses cannot include data or warnings")
            if self.diagnostics is not None:
                raise ValueError("error responses cannot include diagnostics")
        return self


class TextProcessRequest(BaseModel):
    source_text: str = Field(max_length=5000)
