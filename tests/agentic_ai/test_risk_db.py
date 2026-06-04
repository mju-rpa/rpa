"""compute_risk_score: DB 약물정보 기반 채점 + 키워드 폴백(하이브리드)."""
from app.agentic_ai.drug_db.connection import connect
from app.agentic_ai.scoring.risk import compute_risk_score


def _analysis(names, warning=""):
    return {
        "필수복약리스트": [
            {"약품명": n, "복용시간": "1일 1회", "주의사항": ""} for n in names
        ],
        "상호작용_경고": warning,
    }


def _interaction_items(result):
    return [d for d in result["감점항목"] if d.get("근거", "").startswith("DB")]


def test_db_contraindication_deducts_with_evidence(drug_db_path):
    conn = connect(drug_db_path)
    names = ["제클라정", "심바로드정20밀리그람(심바스타틴)"]
    ocr = " ".join(names)
    result = compute_risk_score("", ocr, _analysis(names), conn=conn)

    items = _interaction_items(result)
    assert len(items) == 1
    assert items[0]["감점"] == 30
    assert "횡문근융해" in items[0]["금기사유"]
    assert result["최종점수"] == 70


def test_db_safe_pair_has_no_interaction_deduction(drug_db_path):
    conn = connect(drug_db_path)
    names = ["타이레놀", "심바로드정20밀리그람(심바스타틴)"]
    ocr = " ".join(names)
    result = compute_risk_score("", ocr, _analysis(names), conn=conn)

    assert _interaction_items(result) == []
    assert result["최종점수"] == 100


def test_fallback_to_keyword_when_db_unavailable():
    # conn=None → 기존 키워드 감점 로직(레거시) 유지
    analysis = _analysis(["아무약"], warning="이 약은 우유와 병용 금기입니다")
    result = compute_risk_score("아무약", "아무약", analysis, conn=None)

    assert result["최종점수"] == 70
    assert any("상호작용" in d["항목"] for d in result["감점항목"])
