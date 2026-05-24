from pydantic import BaseModel

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
