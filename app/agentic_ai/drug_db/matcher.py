"""한글 약품명 정규화 및 성분명(영문) 해석.

LLM 분석은 한글 약품명(예: "타이레놀")을 내놓지만, DB의 성분 테이블은
영문 성분명(예: "acetaminophen")을 쓴다. dose_limits / duration_limits 에는
한글 제품명과 영문 성분명이 함께 들어 있어, 외부 사전 없이 DB만으로 해석한다.
"""
import re
import sqlite3

# "_(...)" 포장/규격 꼬리표, "(...)" 성분 표기
_PAREN_TAIL = re.compile(r"_\([^)]*\)")
_PAREN = re.compile(r"\([^)]*\)")
# 용량 토큰: 숫자(+소수) + 단위
_DOSAGE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:밀리그람|밀리그램|마이크로그람|마이크로그램|밀리리터|mg|mcg|µg|ml|g|IU|%)",
    re.IGNORECASE,
)


def normalize_name(raw: str) -> str:
    """제품명을 매칭용 핵심명으로 축약."""
    s = _PAREN_TAIL.sub("", raw)
    s = _PAREN.sub("", s)
    s = _DOSAGE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_ingredients(conn: sqlite3.Connection, drug_name: str) -> set[str]:
    """약품명으로 DB에서 영문 성분명 집합을 해석. 못 찾으면 빈 집합."""
    core = normalize_name(drug_name)
    if not core:
        return set()
    like = f"%{core}%"
    # 1차: 소형 테이블(dose/duration) — 빠름
    rows = conn.execute(
        """
        SELECT DISTINCT 성분명 FROM dose_limits     WHERE 제품명 LIKE ?
        UNION
        SELECT DISTINCT 성분명 FROM duration_limits WHERE 제품명 LIKE ?
        """,
        (like, like),
    ).fetchall()
    ingredients = {r[0] for r in rows if r[0]}
    if ingredients:
        return ingredients
    # 2차 폴백: interactions 제품명 스캔 — 용량규제가 없는 약 해석
    rows = conn.execute(
        """
        SELECT DISTINCT 성분명1 FROM drug_interactions WHERE 제품명1 LIKE ?
        UNION
        SELECT DISTINCT 성분명2 FROM drug_interactions WHERE 제품명2 LIKE ?
        """,
        (like, like),
    ).fetchall()
    return {r[0] for r in rows if r[0]}
