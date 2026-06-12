from dataclasses import dataclass, field as dc_field
from typing import Literal

from pydantic import BaseModel, field_validator

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


class Medicine(BaseModel):
    name: str
    dosage: str | None = None
    frequency: str | None = None
    timing: str | None = None
    caution: str | None = None

    @field_validator("dosage", "frequency", "timing", "caution", mode="before")
    @classmethod
    def coerce_to_str(cls, v):
        if v is None:
            return v
        return str(v)


class OcrResponse(BaseModel):
    patient_name: str | None = None
    prescribed_date: str | None = None
    hospital_name: str | None = None
    medicines: list[Medicine] = []
    general_caution: str | None = None


@dataclass
class ConfidenceResult:
    llm_score: float
    rule_score: float
    score: float
    response: str = ""


@dataclass
class OcrPipelineResult:
    status: Literal["ok", "hitl_required"]
    data: OcrResponse
    confidence: ConfidenceResult
    retried: bool


class DiagnosisResponse(BaseModel):
    patient_name: str | None = None
    birth_date: str | None = None
    diagnosis_name: str | None = None
    hospital_name: str | None = None
    doctor_name: str | None = None
    diagnosis_date: str | None = None
    department: str | None = None
    purpose: str | None = None


@dataclass
class DiagnosisPipelineResult:
    status: Literal["ok", "hitl_required"]
    data: DiagnosisResponse
    confidence: ConfidenceResult
    retried: bool