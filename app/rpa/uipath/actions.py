def build_rpa_actions(
    알림매체: str,
    risk: dict,
    output_dir: str = "output",
) -> list[str]:
    """UiPath For Each / Write Line 시연용 액션 문자열 목록."""
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
