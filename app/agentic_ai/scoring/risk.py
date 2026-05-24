from app.config import RISK_SCORE_REVIEW_THRESHOLD


def compute_risk_score(stt: str, ocr: str, analysis: dict) -> dict:
    """복약 위험도 점수: 100점에서 감점."""
    score = 100
    deductions: list[dict] = []

    warning = analysis.get("상호작용_경고", "")
    meds = analysis.get("필수복약리스트", [])

    high_risk_keywords = ["금기", "병용", "함께 복용하지", "우유"]
    if any(k in warning for k in high_risk_keywords):
        score -= 30
        deductions.append({"항목": "상호작용·복용 주의 경고", "감점": 30})

    ocr_lower = ocr.lower()
    for med in meds:
        name = med.get("약품명", "")
        core = name.split()[0] if name else ""
        if core and core not in ocr and core not in stt:
            score -= 20
            deductions.append({"항목": f"약품명 불일치 의심: {name}", "감점": 20})
            break

    daily_count = sum(
        1 for m in meds if "1일" in m.get("복용시간", "") or "매일" in m.get("주의사항", "")
    )
    if daily_count > 5 or len(meds) > 5:
        score -= 10
        deductions.append({"항목": "복용 횟수 과다·순응도 하락 예상", "감점": 10})

    score = max(0, score)
    needs_review = score < RISK_SCORE_REVIEW_THRESHOLD
    reason = ""
    if needs_review:
        reason = (
            f"위험도 점수 {score}점이 기준({RISK_SCORE_REVIEW_THRESHOLD}점) 미만 — "
            "담당자 재검토 필요"
        )

    return {
        "기본점수": 100,
        "감점항목": deductions,
        "최종점수": score,
        "재검토_필요": needs_review,
        "재검토_사유": reason,
    }
