"""복약 위험도 점수(100점 감점제).

상호작용 감점은 약물안전 DB(drug_safety.db) 조회를 주축으로 한다.
약품이 DB에서 해석되지 않거나 DB가 없으면 기존 키워드 채점으로 폴백한다(하이브리드).
"""
from app.agentic_ai.drug_db.connection import connect
from app.agentic_ai.drug_db.safety import assess
from app.config import (
    DRUG_SAFETY_DB_PATH,
    RISK_SCORE_REVIEW_THRESHOLD,
    drug_db_enabled,
)

_UNSET = object()
_HIGH_RISK_KEYWORDS = ["금기", "병용", "함께 복용하지", "우유"]


def _open_default_conn():
    if not drug_db_enabled():
        return None
    return connect(DRUG_SAFETY_DB_PATH)


def _interaction_deductions(conn, drug_names, analysis) -> list[dict]:
    """상호작용 감점 항목. DB 매칭 성공 시 DB 근거, 아니면 키워드 폴백."""
    if conn is not None and drug_names:
        result = assess(conn, drug_names)
        if result["resolved"]:
            if not result["interactions"]:
                return []
            detail = "; ".join(
                f"{f['약품1']}+{f['약품2']}: {f['금기사유']}"
                for f in result["interactions"]
            )
            return [
                {
                    "항목": "상호작용·병용금기 (DB 확인)",
                    "감점": 30,
                    "근거": "DB:drug_interactions",
                    "금기사유": detail,
                    "약품쌍": [
                        [f["약품1"], f["약품2"]] for f in result["interactions"]
                    ],
                }
            ]

    # 폴백: 분석 텍스트의 키워드로 판정 (레거시)
    warning = analysis.get("상호작용_경고", "")
    if any(k in warning for k in _HIGH_RISK_KEYWORDS):
        return [{"항목": "상호작용·복용 주의 경고", "감점": 30}]
    return []


def compute_risk_score(stt: str, ocr: str, analysis: dict, conn=_UNSET) -> dict:
    """복약 위험도 점수: 100점에서 감점."""
    if conn is _UNSET:
        conn = _open_default_conn()

    score = 100
    deductions: list[dict] = []
    meds = analysis.get("필수복약리스트", [])
    drug_names = [m.get("약품명", "") for m in meds if m.get("약품명")]

    # ── 1. 상호작용·병용금기 (DB 주축 + 키워드 폴백) ──
    for item in _interaction_deductions(conn, drug_names, analysis):
        score -= item["감점"]
        deductions.append(item)

    # ── 2. 약품명 불일치 (OCR/STT 대조) ──
    for med in meds:
        name = med.get("약품명", "")
        core = name.split()[0] if name else ""
        if core and core not in ocr and core not in stt:
            score -= 20
            deductions.append({"항목": f"약품명 불일치 의심: {name}", "감점": 20})
            break

    # ── 3. 복용 횟수 과다 ──
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
