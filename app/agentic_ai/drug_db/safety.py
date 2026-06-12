"""DB 약물정보 기반 안전성 조회.

v1: 병용금기(drug_interactions) 조회. 약품명 → 성분명(영문) 해석 후
성분명 쌍으로 금기 여부를 확인한다(성분명1/2 인덱스 활용).
"""
import sqlite3
from itertools import combinations

from app.agentic_ai.drug_db.matcher import resolve_ingredients


def _pair_contraindication(
    conn: sqlite3.Connection, a: set[str], b: set[str]
) -> str | None:
    """성분 집합 a, b 사이 금기사유. 없으면 None."""
    qa = ",".join("?" * len(a))
    qb = ",".join("?" * len(b))
    row = conn.execute(
        f"""
        SELECT 금기사유 FROM drug_interactions
        WHERE (성분명1 IN ({qa}) AND 성분명2 IN ({qb}))
           OR (성분명1 IN ({qb}) AND 성분명2 IN ({qa}))
        LIMIT 1
        """,
        (*a, *b, *b, *a),
    ).fetchone()
    return row[0] if row else None


def assess(conn: sqlite3.Connection, drug_names: list[str]) -> dict:
    """약품 목록을 한 번 해석해 매칭 여부와 병용금기 목록을 함께 반환.

    returns {"resolved": bool, "interactions": [{"약품1","약품2","금기사유"}]}
    - resolved: 약품 중 하나라도 DB에서 성분 해석됨 (하이브리드 분기 신호)
    """
    resolved = {name: resolve_ingredients(conn, name) for name in drug_names}
    findings: list[dict] = []
    for name1, name2 in combinations(drug_names, 2):
        ing1, ing2 = resolved[name1], resolved[name2]
        if not ing1 or not ing2:
            continue
        reason = _pair_contraindication(conn, ing1, ing2)
        if reason:
            findings.append({"약품1": name1, "약품2": name2, "금기사유": reason})
    return {
        "resolved": any(resolved.values()),
        "interactions": findings,
    }


def check_interactions(
    conn: sqlite3.Connection, drug_names: list[str]
) -> list[dict]:
    """약품 목록의 모든 쌍에 대해 병용금기를 조회."""
    return assess(conn, drug_names)["interactions"]
