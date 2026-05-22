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
