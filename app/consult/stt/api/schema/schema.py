from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from app.consult.ocr.api.schema.schema import ConfidenceResult

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


class SpeakerSegment(BaseModel):
    speaker: str
    text: str
    start: float
    end: float


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration: float
    segments: list[SpeakerSegment] = []


@dataclass
class SttPipelineResult:
    status: Literal["ok", "hitl_required"]
    data: TranscribeResponse
    confidence: ConfidenceResult
    retried: bool