def flatten_for_uipath(
    analysis: dict,
    risk: dict,
    reflection_lines: list[str],
    agent_trace_lines: list[str],
    report_text: str,
    report_file: str,
    hidl_status: str = "skipped",
) -> dict:
    """UiPath Deserialize JSON — 영문 flat 키만 사용."""
    return {
        "patient_name": analysis.get("환자명", ""),
        "final_score": risk.get("최종점수", 0 if risk.get("군집") == "위험" else 70 if risk.get("군집") == "주의" else 100),
        "needs_review": risk.get("재검토_필요", risk.get("HITL_필요", False)),
        "risk_cluster": risk.get("군집", "일반"),
        "hidl_status": hidl_status,
        "reflection_summary": "\n".join(reflection_lines),
        "agent_trace_summary": "\n".join(agent_trace_lines),
        "report_text": report_text,
        "report_file": report_file,
    }
