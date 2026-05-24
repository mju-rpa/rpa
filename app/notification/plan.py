from datetime import datetime, timedelta


def build_notification_plan(
    알림매체: str,
    analysis: dict,
    contact: dict,
    risk: dict,
) -> dict:
    """[To-Be] 카톡/구글캘린더 API 연동 전 RPA·notification이 수행할 액션 계획."""
    patient = analysis.get("환자명", "환자")
    events = []
    base = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    for i, med in enumerate(analysis.get("필수복약리스트", [])):
        events.append(
            {
                "title": f"[복약] {med.get('약품명')}",
                "start": (base + timedelta(days=i)).isoformat(),
                "notes": f"{med.get('복용시간')} | {med.get('주의사항')}",
                "status": "to_be_generated",
            }
        )

    if risk.get("재검토_필요"):
        channel_msg = "담당 의료진 메신저로 재검토 플래그 전송 (to_be_generated)"
    elif 알림매체 == "kakao":
        channel_msg = f"카카오 알림 예약 → {contact.get('카카오_id') or contact.get('전화번호', 'N/A')}"
    elif 알림매체 == "google_calendar":
        channel_msg = f"Google Calendar 등록 예약 → {contact.get('google_calendar_email', 'N/A')}"
    elif 알림매체 == "sms":
        channel_msg = f"SMS 발송 예약 → {contact.get('전화번호', 'N/A')}"
    else:
        channel_msg = "알림 매체 미지정 — 리포트 파일만 생성"

    return {
        "알림매체": 알림매체,
        "status": "demo_scheduled",
        "message": f"[{patient}] {channel_msg}",
        "calendar_events": events,
    }
