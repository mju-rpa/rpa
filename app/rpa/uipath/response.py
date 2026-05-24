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
        "final_score": risk["최종점수"],
        "needs_review": risk["재검토_필요"],
        "hidl_status": hidl_status,
        "reflection_summary": "\n".join(reflection_lines),
        "agent_trace_summary": "\n".join(agent_trace_lines),
        "report_text": report_text,
        "report_file": report_file,
    }
