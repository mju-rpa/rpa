from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ContactInfo(BaseModel):
    전화번호: str = ""
    카카오_id: str = ""
    google_calendar_email: str = ""


class AnalyzeRequest(BaseModel):
    patient_name: str = ""
    patient_phone: str = ""
    환자명: str = ""
    알림매체: Literal["kakao", "google_calendar", "sms", "none"] = "none"
    연락처: ContactInfo = Field(default_factory=ContactInfo)
    # 구조화된 STT/OCR 결과 — /input-process 응답 형태.
    #   stt: {text, language, duration, segments:[{speaker,text,start,end}]}
    #   ocr: {prescribed_date, hospital_name, medicines:[...], general_caution}
    stt: dict = Field(default_factory=dict)
    ocr: dict = Field(default_factory=dict)
    # 평탄화 텍스트 — agentic 파이프라인(collect_convert)이 사용.
    # 구조화 stt/ocr만 들어온 경우 validator가 자동 backfill.
    stt_text: str = ""
    ocr_text: str = ""
    diagnosis_text: str = ""
    # OCR/STT 인식 신뢰도 기반 HITL 신호 — {"ocr": {...}, "stt": {...}}
    # /input-process 가 채워서 반환. 점수 낮으면 채널별 status="hitl_required".
    hitl: dict = Field(default_factory=dict)
    # HIDL (Human-In-The-Loop) — 미구현 시 기본값으로 파이프라인 통과
    hidl_enabled: bool = False
    hidl_approved: bool | None = None  # None=미검토, True/False=사용자 결정

    @model_validator(mode="after")
    def _backfill_flat_text(self):
        """구조화 stt/ocr만 있고 평탄화 텍스트가 비면 backfill (재수집 호환)."""
        if not self.stt_text and self.stt:
            self.stt_text = self.stt.get("text", "") or ""
        if not self.ocr_text and self.ocr:
            from app.consult.ocr.api.schema.schema import OcrResponse
            from app.consult.ocr.service import to_text as ocr_to_text
            self.ocr_text = ocr_to_text(
                OcrResponse(patient_name=self.patient_name or None, **self.ocr)
            )
        return self


class MedicationItem(BaseModel):
    약품명: str
    복용시간: str
    주의사항: str


class AnalysisResult(BaseModel):
    환자명: str
    진료요약: str
    필수복약리스트: list[MedicationItem]
    상호작용_경고: str


class ScoreDetail(BaseModel):
    기본점수: int = 100
    감점항목: list[dict] = Field(default_factory=list)
    최종점수: int = 100
    재검토_필요: bool = False
    재검토_사유: str = ""


class ReflectionLog(BaseModel):
    round: int
    critic_feedback: str
    revised: bool


class NotificationPlan(BaseModel):
    알림매체: str
    status: str
    message: str
    calendar_events: list[dict] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    workflow_stage: str
    analysis: AnalysisResult
    risk_score: ScoreDetail
    reflection_logs: list[ReflectionLog]
    notification_plan: NotificationPlan
    rpa_actions: list[str]
    report_text: str
