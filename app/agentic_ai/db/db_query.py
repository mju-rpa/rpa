"""
db_query.py
약물 DB 조회 인터페이스

벡터 DB: ChromaDB (chroma_db/)
  - 오픈소스, 로컬 실행, 별도 서버 불필요
  - pip install chromadb

관계형 DB: SQLite (drug_safety.db)
  - Python 내장, 별도 설치 불필요

할루시네이션 방지 전략 3가지 적용:
  1. 메타데이터 필터링  → 벡터 검색 전 약품명으로 먼저 필터
  2. 하이브리드 검색    → 관계형 정확 매칭 먼저, 실패 시 벡터 검색
  3. 원본 텍스트 전달   → 출처 명시한 원본 텍스트 그대로 LLM에 전달

사용법:
    from db_query import DrugDB
    db = DrugDB()
    result = db.query_all("넥시움정", "타이레놀정")
    context = db.build_rag_context("넥시움정", "타이레놀정")
"""

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

import chromadb

# ── 경로 설정 ──────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
RELATIONAL_DB = os.path.join(BASE_DIR, "drug_safety.db")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "chroma_db")


@dataclass
class DrugWarning:
    """주의사항 분류 결과."""
    심각:   list = field(default_factory=list)
    주의:   list = field(default_factory=list)
    참고:   list = field(default_factory=list)
    용량초과: list = field(default_factory=list)
    기간초과: list = field(default_factory=list)
    노인주의: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "심각":    self.심각,
            "주의":    self.주의,
            "참고":    self.참고,
            "용량초과": self.용량초과,
            "기간초과": self.기간초과,
            "노인주의": self.노인주의,
            "총_건수": {
                "심각":    len(self.심각),
                "주의":    len(self.주의),
                "참고":    len(self.참고),
                "용량초과": len(self.용량초과),
                "기간초과": len(self.기간초과),
                "노인주의": len(self.노인주의),
            }
        }


class DrugDB:
    """
    관계형 DB + 벡터 DB 통합 조회 클래스.

    사용한 벡터 DB: ChromaDB
      - 로컬 파일 기반 (chroma_db/ 폴더)
      - 임베딩: all-MiniLM-L6-v2 (기본) 또는 한국어 특화 모델
      - 설치: pip install chromadb
    """

    def __init__(self):
        self._rel = sqlite3.connect(RELATIONAL_DB)
        self._rel.row_factory = sqlite3.Row
        self._vec = chromadb.PersistentClient(path=VECTOR_DB_DIR)

    def close(self):
        self._rel.close()

    # ══════════════════════════════════════════════════════════
    # 관계형 DB 조회
    # ══════════════════════════════════════════════════════════

    def get_drug_info(self, drug_name: str) -> Optional[dict]:
        """약품명으로 기본 정보 조회."""
        cur = self._rel.cursor()
        cur.execute(
            "SELECT * FROM drugs WHERE item_name LIKE ?",
            (f"%{drug_name}%",)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def check_interaction(self, drug1: str, drug2: str) -> list[dict]:
        """두 약품의 병용금기 여부 확인."""
        cur = self._rel.cursor()
        cur.execute(
            """
            SELECT 제품명1, 제품명2, 성분명1, 성분명2, 금기사유
            FROM drug_interactions
            WHERE (제품명1 LIKE ? AND 제품명2 LIKE ?)
               OR (제품명1 LIKE ? AND 제품명2 LIKE ?)
            LIMIT 10
            """,
            (f"%{drug1}%", f"%{drug2}%",
             f"%{drug2}%", f"%{drug1}%"),
        )
        return [dict(r) for r in cur.fetchall()]

    def check_dose_limit(self, drug_name: str, daily_dose_mg: float) -> Optional[dict]:
        """1일 복용량 초과 여부 확인."""
        cur = self._rel.cursor()
        cur.execute(
            """
            SELECT 제품명, 성분명, 일최대투여량, 일최대투여기준량_mg
            FROM dose_limits
            WHERE 제품명 LIKE ? AND 일최대투여기준량_mg IS NOT NULL
            LIMIT 1
            """,
            (f"%{drug_name}%",),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            **dict(row),
            "처방용량_mg": daily_dose_mg,
            "초과여부": daily_dose_mg > row["일최대투여기준량_mg"],
        }

    def check_duration_limit(self, drug_name: str, prescribed_days: int) -> Optional[dict]:
        """투여기간 초과 여부 확인."""
        cur = self._rel.cursor()
        cur.execute(
            """
            SELECT 제품명, 성분명, 최대투여기간일수
            FROM duration_limits
            WHERE 제품명 LIKE ? AND 최대투여기간일수 IS NOT NULL
            LIMIT 1
            """,
            (f"%{drug_name}%",),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            **dict(row),
            "처방기간_일": prescribed_days,
            "초과여부": prescribed_days > row["최대투여기간일수"],
        }

    # ══════════════════════════════════════════════════════════
    # 벡터 DB 조회 — 방법 1: 메타데이터 필터링
    # ══════════════════════════════════════════════════════════

    def search_warnings_filtered(
        self,
        query: str,
        item_name: str,         # 약품명으로 먼저 필터
        warn_type: str = None,  # "상호작용" / "주의사항" / "부작용"
        n: int = 3,
    ) -> list[dict]:
        """
        [방법 1] 메타데이터 필터링 적용 벡터 검색.

        벡터 검색 전에 item_name으로 필터 → 관련 없는 약품 문서 제거
        → 할루시네이션 원인인 엉뚱한 약품 정보 섞임 방지

        Args:
            query     : 검색 쿼리 (자연어)
            item_name : 약품명 필터 (정확한 item_name 값)
            warn_type : 문서 유형 필터 (선택)
            n         : 반환 결과 수
        """
        try:
            col = self._vec.get_collection("drug_warnings")

            # 메타데이터 필터 구성
            where = {"item_name": item_name}
            if warn_type:
                where = {"$and": [{"item_name": item_name}, {"type": warn_type}]}

            try:
                result = col.query(
                    query_texts=[query],
                    where=where,
                    n_results=n,
                )
            except Exception:
                # 해당 약품 데이터 없으면 필터 없이 검색
                result = col.query(query_texts=[query], n_results=n)
        except Exception:
            return []

        return [
            {
                "document": doc,
                "metadata": meta,
                "distance": dist,
            }
            for doc, meta, dist in zip(
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]

    def search_elderly_filtered(
        self, query: str, drug_name: str, n: int = 3
    ) -> list[dict]:
        """
        [방법 1] 메타데이터 필터링 적용 노인주의 검색.
        """
        try:
            col = self._vec.get_collection("elderly_warnings")
            try:
                result = col.query(
                    query_texts=[query],
                    where={"제품명": drug_name},
                    n_results=n,
                )
            except Exception:
                result = col.query(query_texts=[query], n_results=n)
        except Exception:
            return []

        return [
            {"document": doc, "metadata": meta}
            for doc, meta in zip(
                result["documents"][0], result["metadatas"][0]
            )
        ]

    # ══════════════════════════════════════════════════════════
    # 방법 2: 하이브리드 검색
    # ══════════════════════════════════════════════════════════

    def hybrid_search(self, drug_name: str) -> dict:
        """
        [방법 2] 하이브리드 검색.

        1단계: 관계형 DB 정확 매칭
        2단계: 정확 매칭 실패 시에만 벡터 검색으로 보완

        → LLM에 전달하는 컨텍스트 신뢰도 향상
        → 관계형 DB 결과 = 정확한 공식 데이터
        → 벡터 DB 결과 = 의미적으로 유사한 보완 정보
        """
        result = {
            "drug_name": drug_name,
            "source": None,
            "info": None,
            "supplementary": [],
        }

        # 1단계: 관계형 DB 정확 매칭
        drug_info = self.get_drug_info(drug_name)

        if drug_info:
            result["source"] = "관계형_DB_정확매칭"
            result["info"]   = drug_info

            # 정확 매칭 성공해도 벡터 DB로 추가 맥락 보완
            extra = self.search_warnings_filtered(
                query=f"{drug_name} 주의사항 금기",
                item_name=drug_info["item_name"],
                n=2,
            )
            result["supplementary"] = extra

        else:
            # 2단계: 정확 매칭 실패 → 벡터 검색으로 유사 약품 찾기
            result["source"] = "벡터_DB_유사검색"
            try:
                col = self._vec.get_collection("drug_warnings")
                vec_result = col.query(
                    query_texts=[f"{drug_name} 주의사항"],
                    n_results=3,
                )
                result["supplementary"] = [
                    {"document": doc, "metadata": meta}
                    for doc, meta in zip(
                        vec_result["documents"][0],
                        vec_result["metadatas"][0],
                    )
                ]
            except Exception:
                result["supplementary"] = []

        return result

    # ══════════════════════════════════════════════════════════
    # 방법 3: 원본 텍스트 + 출처 명시 RAG 컨텍스트 생성
    # ══════════════════════════════════════════════════════════

    def build_rag_context(self, *drug_names: str) -> str:
        """
        [방법 3] LLM에 전달할 RAG 컨텍스트 생성.

        출처를 명시한 원본 텍스트 그대로 전달
        → LLM이 "DB에 없는 내용을 지어내는" 할루시네이션 방지
        → LLM 프롬프트에 "아래 DB 정보만 기반으로 판단하라" 지시와 함께 사용

        Returns:
            str: LLM 프롬프트에 삽입할 컨텍스트 문자열
        """
        context_blocks = []

        for drug in drug_names:
            block_lines = [f"[약품: {drug}]"]

            # 관계형 DB 원본 텍스트 (정확한 공식 데이터)
            info = self.get_drug_info(drug)
            if info:
                if info.get("intrc") and info["intrc"] != "정보 없음":
                    block_lines.append(
                        f"  - 상호작용 (출처: 식약처 e약은요): {info['intrc']}"
                    )
                if info.get("atpn") and info["atpn"] != "정보 없음":
                    block_lines.append(
                        f"  - 주의사항 (출처: 식약처 e약은요): {info['atpn'][:300]}"
                    )
                if info.get("se") and str(info.get("se")) != "정보 없음":
                    block_lines.append(
                        f"  - 부작용 (출처: 식약처 e약은요): {str(info['se'])[:200]}"
                    )
            else:
                block_lines.append("  - 관계형 DB: 약품 정보 없음")

            context_blocks.append("\n".join(block_lines))

        # 병용금기 (두 약품 이상일 때)
        drugs = list(drug_names)
        inter_lines = []
        for i in range(len(drugs)):
            for j in range(i + 1, len(drugs)):
                inters = self.check_interaction(drugs[i], drugs[j])
                for inter in inters[:3]:  # 최대 3개
                    inter_lines.append(
                        f"  - {inter['제품명1']} + {inter['제품명2']}: "
                        f"{inter['금기사유']} (출처: 식약처 병용금기)"
                    )

        if inter_lines:
            context_blocks.append(
                "[병용금기 확인]\n" + "\n".join(inter_lines)
            )

        # 컨텍스트 조립
        context = "\n\n".join(context_blocks)
        context += "\n\n[주의] 위 정보는 식약처 공식 DB에서 가져온 원본 데이터입니다."
        context += "\n위 정보에 없는 내용은 절대 추측하거나 생성하지 마십시오."
        context += "\n정보가 없는 경우 '데이터 없음'으로 표시하십시오."

        return context

    # ══════════════════════════════════════════════════════════
    # 통합 조회 (Agent용)
    # ══════════════════════════════════════════════════════════

    def query_all(
        self,
        *drug_names: str,
        daily_doses:     dict = None,
        prescribed_days: dict = None,
    ) -> DrugWarning:
        """
        여러 약품 전체 주의사항 조회.
        방법 1(메타데이터 필터링) + 방법 2(하이브리드) 모두 적용.

        CrewAI RiskEvaluator Agent에서 호출.
        """
        daily_doses     = daily_doses     or {}
        prescribed_days = prescribed_days or {}
        result          = DrugWarning()
        drugs           = list(drug_names)

        # 1. 병용금기 (관계형 DB 정확 매칭)
        for i in range(len(drugs)):
            for j in range(i + 1, len(drugs)):
                for inter in self.check_interaction(drugs[i], drugs[j]):
                    사유 = inter.get("금기사유", "")
                    item = {
                        "약품1":  inter["제품명1"],
                        "약품2":  inter["제품명2"],
                        "내용":  사유,
                        "출처":  "식약처 병용금기",
                    }
                    if any(k in 사유 for k in ["복용하지 마", "금기", "사용하지 마"]):
                        result.심각.append(item)
                    else:
                        result.주의.append(item)

        # 2. 자연어 주의사항 (방법 1: 메타데이터 필터 벡터 검색)
        for drug in drugs:
            # 먼저 관계형 DB로 정확한 item_name 확인 (방법 2)
            info = self.get_drug_info(drug)
            item_name = info["item_name"] if info else drug

            # 메타데이터 필터 적용 벡터 검색 (방법 1)
            warnings = self.search_warnings_filtered(
                query=f"{drug} 주의사항 금기 복용 금지",
                item_name=item_name,
                n=3,
            )
            for w in warnings:
                doc  = w["document"]
                meta = w["metadata"]
                item = {
                    "약품명": meta.get("item_name", drug),
                    "내용":  doc[:150],
                    "유형":  meta.get("type", ""),
                    "출처":  "식약처 e약은요",
                }
                if any(k in doc for k in ["복용하지 마", "사용하지 마", "금기"]):
                    result.심각.append(item)
                elif any(k in doc for k in ["상의하십시오", "의사 또는 약사"]):
                    result.주의.append(item)
                else:
                    result.참고.append(item)

        # 3. 용량 초과 (관계형 DB 수치 비교)
        for drug, dose in daily_doses.items():
            check = self.check_dose_limit(drug, dose)
            if check and check["초과여부"]:
                result.용량초과.append({
                    "약품명": check["제품명"],
                    "내용":  f"1일 최대 {check['일최대투여량']} 초과 (처방: {dose}mg)",
                    "출처":  "식약처 용량주의",
                })

        # 4. 기간 초과 (관계형 DB 수치 비교)
        for drug, days in prescribed_days.items():
            check = self.check_duration_limit(drug, days)
            if check and check["초과여부"]:
                result.기간초과.append({
                    "약품명": check["제품명"],
                    "내용":  f"최대 {check['최대투여기간일수']}일 초과 (처방: {days}일)",
                    "출처":  "식약처 투여기간주의",
                })

        # 5. 노인주의 (방법 1: 메타데이터 필터 벡터 검색)
        for drug in drugs:
            info      = self.get_drug_info(drug)
            item_name = info["item_name"] if info else drug
            for e in self.search_elderly_filtered(
                query=f"{drug} 노인 위험 낙상",
                drug_name=item_name,
                n=2,
            ):
                result.노인주의.append({
                    "약품명": e["metadata"].get("제품명", drug),
                    "내용":  e["document"][:150],
                    "출처":  "식약처 노인주의",
                })

        return result


# ── 직접 실행 시 테스트 ────────────────────────────────────────
if __name__ == "__main__":
    db = DrugDB()

    print("=" * 55)
    print("테스트 1: 방법 1 (메타데이터 필터링)")
    print("=" * 55)
    results = db.search_warnings_filtered(
        query="우유와 함께 복용 금지",
        item_name="넥시움정",
        warn_type="상호작용",
    )
    for r in results:
        print(f"  [{r['metadata']['type']}] {r['document'][:80]}")

    print()
    print("=" * 55)
    print("테스트 2: 방법 2 (하이브리드 검색)")
    print("=" * 55)
    hybrid = db.hybrid_search("넥시움정")
    print(f"  검색 소스: {hybrid['source']}")
    if hybrid["info"]:
        print(f"  약품명: {hybrid['info']['item_name']}")
        print(f"  상호작용: {str(hybrid['info']['intrc'])[:80]}")

    print()
    print("=" * 55)
    print("테스트 3: 방법 3 (원본 텍스트 RAG 컨텍스트)")
    print("=" * 55)
    context = db.build_rag_context("넥시움정", "타이레놀정")
    print(context[:500])

    print()
    print("=" * 55)
    print("테스트 4: 통합 조회 (query_all)")
    print("=" * 55)
    warnings = db.query_all("넥시움정", "타이레놀정")
    w = warnings.to_dict()
    for 분류, items in w.items():
        if 분류 == "총_건수":
            print(f"\n총 건수: {items}")
        elif items:
            print(f"\n{분류}:")
            for item in items[:2]:
                print(f"  → {item.get('내용', '')[:60]}")

    db.close()
