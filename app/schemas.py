from typing import Literal

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    전화번호: str = ""
    카카오_id: str = ""
    google_calendar_email: str = ""


class AnalyzeRequest(BaseModel):
    patient_id: str = ""
    환자명: str = ""
    알림매체: Literal["kakao", "google_calendar", "sms", "none"] = "none"
    연락처: ContactInfo = Field(default_factory=ContactInfo)
    stt_text: str = ""
    ocr_text: str = ""
    # 파일 업로드 대신 JSON body로 받음 (UiPath HTTP Request와 동일)


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
    status: str  # demo_scheduled | to_be_generated
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
