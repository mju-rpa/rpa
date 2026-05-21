from datetime import datetime, timedelta


def build_notification_plan(
    알림매체: str,
    analysis: dict,
    contact: dict,
    risk: dict,
) -> dict:
    """[To-Be Generated] 실제 카톡/구글캘린더 API 연동 전 RPA가 수행할 액션 계획."""
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


def build_rpa_actions(
    알림매체: str,
    risk: dict,
    output_dir: str = "output",
) -> list[str]:
    actions = [
        f"[RPA] Excel 리포트 저장 → {output_dir}/{{환자명}}_복약리포트.xlsx (to_be_generated)",
        f"[RPA] 텍스트 리포트 저장 → {output_dir}/Medical_Report_Demo.txt",
    ]
    if risk.get("재검토_필요"):
        actions.append("[RPA] 담당자 플래그 — 사내 메신저/이메일 경고 (to_be_generated)")
    if 알림매체 == "kakao":
        actions.append("[RPA] Kakao API Webhook 호출 (to_be_generated)")
    elif 알림매체 == "google_calendar":
        actions.append("[RPA] Google Calendar API — OAuth2 일정 생성 (to_be_generated)")
    elif 알림매체 == "sms":
        actions.append("[RPA] SMS 게이트웨이 호출 (to_be_generated)")
    return actions


def format_report(analysis: dict, risk: dict) -> str:
    lines = [
        "======================================",
        "[Atlas 메디케어] 맞춤형 진료/복약 리포트",
        f"발행일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "======================================",
        f"👤 환자명: {analysis.get('환자명')}",
        "",
        "📋 [진료 요약]",
        analysis.get("진료요약", ""),
        "",
        "💊 [복약 스케줄]",
    ]
    for med in analysis.get("필수복약리스트", []):
        lines.append(
            f" - {med.get('약품명')} | {med.get('복용시간')} | 주의: {med.get('주의사항')}"
        )
    lines.extend(
        [
            "",
            "⚠️ [특별 주의사항]",
            analysis.get("상호작용_경고", ""),
            "",
            f"📊 [복약 위험도 점수] {risk.get('최종점수')} / 100",
            f"   재검토 필요: {'예' if risk.get('재검토_필요') else '아니오'}",
            "======================================",
        ]
    )
    return "\n".join(lines)
