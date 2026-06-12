from app.agentic_ai.drug_db.connection import connect
from app.agentic_ai.drug_db.safety import assess, check_interactions


def test_assess_reports_resolution_and_interactions(drug_db_path):
    conn = connect(drug_db_path)
    result = assess(conn, ["제클라정", "심바로드정20밀리그람(심바스타틴)"])
    assert result["resolved"] is True
    assert len(result["interactions"]) == 1
    assert "횡문근융해" in result["interactions"][0]["금기사유"]


def test_assess_unresolved_drugs_report_not_resolved(drug_db_path):
    conn = connect(drug_db_path)
    result = assess(conn, ["존재하지않는약1", "존재하지않는약2"])
    assert result["resolved"] is False
    assert result["interactions"] == []


def test_contraindicated_pair_is_flagged(drug_db_path):
    conn = connect(drug_db_path)
    findings = check_interactions(conn, ["제클라정", "심바로드정20밀리그람(심바스타틴)"])
    assert len(findings) == 1
    f = findings[0]
    assert "횡문근융해" in f["금기사유"]
    assert {f["약품1"], f["약품2"]} == {"제클라정", "심바로드정20밀리그람(심바스타틴)"}


def test_single_drug_has_no_interaction(drug_db_path):
    conn = connect(drug_db_path)
    assert check_interactions(conn, ["타이레놀"]) == []


def test_non_contraindicated_pair_is_not_flagged(drug_db_path):
    conn = connect(drug_db_path)
    assert check_interactions(conn, ["타이레놀", "심바로드정20밀리그람(심바스타틴)"]) == []


def test_unresolvable_drug_is_skipped(drug_db_path):
    conn = connect(drug_db_path)
    assert check_interactions(conn, ["제클라정", "존재하지않는약"]) == []
