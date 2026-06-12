import pytest

from app.agentic_ai.drug_db.connection import connect
from app.agentic_ai.drug_db.matcher import normalize_name, resolve_ingredients


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("타이레놀정500밀리그람(아세트아미노펜)", "타이레놀정"),
        ("제클라정(클래리트로마이신)_(0.25g/1정)", "제클라정"),
        ("리스카펜정_(1정)", "리스카펜정"),
        ("타이레놀", "타이레놀"),
        ("  타이레놀  ", "타이레놀"),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_resolve_ingredients_matches_korean_name(drug_db_path):
    conn = connect(drug_db_path)
    assert resolve_ingredients(conn, "타이레놀") == {"acetaminophen"}


def test_resolve_ingredients_matches_full_product_name(drug_db_path):
    conn = connect(drug_db_path)
    assert resolve_ingredients(conn, "제클라정(클래리트로마이신)_(0.25g/1정)") == {
        "clarithromycin"
    }


def test_resolve_ingredients_falls_back_to_interactions(drug_db_path):
    # dose_limits/duration_limits 에 없어도 interactions 제품명으로 해석돼야 함
    conn = connect(drug_db_path)
    assert resolve_ingredients(conn, "와파린") == {"warfarin"}


def test_resolve_ingredients_unknown_drug_returns_empty(drug_db_path):
    conn = connect(drug_db_path)
    assert resolve_ingredients(conn, "존재하지않는약") == set()
