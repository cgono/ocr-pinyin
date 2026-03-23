from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OcrSegment(BaseModel):
    text: str
    language: str
    confidence: float = Field(ge=0.0, le=1.0)


class OcrData(BaseModel):
    segments: list[OcrSegment]


class PinyinSegment(BaseModel):
    hanzi: str
    pinyin: str


class PinyinData(BaseModel):
    segments: list[PinyinSegment]


class ProcessData(BaseModel):
    model_config = ConfigDict(extra="allow")

    ocr: OcrData | None = None
    pinyin: PinyinData | None = None
    message: str | None = None
    job_id: str | None = None


class ProcessWarning(BaseModel):
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

    @model_validator(mode="after")
    def validate_status_envelope(self) -> "ProcessResponse":
        if self.status == "success":
            if self.data is None:
                raise ValueError("success responses require data")
            if self.warnings is not None or self.error is not None:
                raise ValueError("success responses cannot include warnings or error")
        elif self.status == "partial":
            if self.data is None or self.warnings is None:
                raise ValueError("partial responses require data and warnings")
            if self.error is not None:
                raise ValueError("partial responses cannot include error")
        elif self.status == "error":
            if self.error is None:
                raise ValueError("error responses require error")
            if self.data is not None or self.warnings is not None:
                raise ValueError("error responses cannot include data or warnings")
        return self
