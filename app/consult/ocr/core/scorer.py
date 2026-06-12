import logging
import sqlite3

from app.consult.ocr.api.schema.schema import ConfidenceResult, DiagnosisResponse, OcrResponse
from app.consult.ocr.core.config import ocr_config
from app.config import DRUG_SAFETY_DB_PATH
from app.agentic_ai.drug_db.connection import connect as db_connect

logger = logging.getLogger(__name__)

_db_conn: sqlite3.Connection | None = None


def _get_db() -> sqlite3.Connection | None:
    global _db_conn
    if _db_conn is None:
        _db_conn = db_connect(DRUG_SAFETY_DB_PATH)
        if _db_conn is None:
            logger.warning("[OcrScorer] drug_safety.db 없음 — DB 검증 건너뜀")
    return _db_conn


def _drug_exists_in_db(conn: sqlite3.Connection, name: str) -> bool:
    """item_name LIKE '%name%' 로 drugs 테이블에서 약품 존재 여부 확인."""
    if not name or not name.strip():
        return False
    row = conn.execute(
        "SELECT 1 FROM drugs WHERE item_name LIKE ? LIMIT 1",
        (f"%{name.strip()}%",),
    ).fetchone()
    return row is not None


class OcrScorer:
    def score(
        self,
        response: OcrResponse,
        llm_score: float,
        llm_reason: str = "",
        blur_var: float | None = None,
    ) -> ConfidenceResult:
        rule_score, parts = self._rule_score(response, blur_var)
        score = round(llm_score * 0.5 + rule_score * 0.5, 4)
        resp_text = " | ".join(parts)
        if llm_reason:
            resp_text += f" | LLM: {llm_reason}"
        logger.debug("[OcrScorer] llm=%.2f rule=%.2f score=%.2f", llm_score, rule_score, score)
        return ConfidenceResult(
            llm_score=llm_score,
            rule_score=rule_score,
            score=score,
            response=resp_text,
        )

    def _rule_score(self, r: OcrResponse, blur_var: float | None) -> tuple[float, list[str]]:
        # rule = 약품추출(0.4) + DB매칭(0.4) + 선명도(0.2)
        score = 0.0
        parts: list[str] = []

        # (1) 약품 존재 여부 (0.4)
        if r.medicines:
            score += 0.4
            parts.append(f"약품 {len(r.medicines)}개 추출됨")

            # (2) DB에 존재하는 약품명이 하나라도 있는지 (0.4)
            conn = _get_db()
            if conn is not None:
                db_matched = any(
                    _drug_exists_in_db(conn, m.name)
                    for m in r.medicines
                    if m.name
                )
                if db_matched:
                    score += 0.4
                    parts.append("DB 약품명 확인")
                else:
                    names = [m.name for m in r.medicines if m.name]
                    parts.append(f"DB 약품명 미확인: {', '.join(names)}")
                    logger.info("[OcrScorer] DB에서 약품명 미확인: %s", names)
            else:
                score += 0.4
                parts.append("DB 미가용(패스)")
        else:
            parts.append("약품 없음")

        # (3) 이미지 선명도/흔들림 (0.2)
        sharp_score, sharp_part = self._sharpness_subscore(blur_var)
        score += sharp_score
        parts.append(sharp_part)

        return round(score, 4), parts

    @staticmethod
    def _sharpness_subscore(blur_var: float | None) -> tuple[float, str]:
        """라플라시안 분산 → 0~0.2 점수. blur_min~blur_good 사이 선형 정규화."""
        if blur_var is None:
            return 0.2, "선명도 측정불가(패스)"
        lo, hi = ocr_config.blur_min, ocr_config.blur_good
        norm = max(0.0, min(1.0, (blur_var - lo) / (hi - lo))) if hi > lo else 1.0
        label = "선명" if norm >= 0.5 else "흔들림 의심"
        return round(norm * 0.2, 4), f"{label}(blur={blur_var:.0f})"


class DiagnosisScorer:
    def score(self, response: DiagnosisResponse, llm_score: float, llm_reason: str = "") -> ConfidenceResult:
        rule_score, parts = self._rule_score(response)
        score = round(llm_score * 0.5 + rule_score * 0.5, 4)
        resp_text = " | ".join(parts)
        if llm_reason:
            resp_text += f" | LLM: {llm_reason}"
        logger.debug("[DiagnosisScorer] llm=%.2f rule=%.2f score=%.2f", llm_score, rule_score, score)
        return ConfidenceResult(llm_score=llm_score, rule_score=rule_score, score=score, response=resp_text)

    def _rule_score(self, r: DiagnosisResponse) -> tuple[float, list[str]]:
        score = 0.0
        parts: list[str] = []

        if r.diagnosis_name:
            score += 0.5
            parts.append(f"진단명 확인({r.diagnosis_name})")
        else:
            parts.append("진단명 없음")

        if r.hospital_name or r.doctor_name:
            score += 0.3
            parts.append("병원/의사 확인")
        else:
            parts.append("병원·의사명 없음")

        if r.patient_name:
            score += 0.2
            parts.append("환자명 확인")
        else:
            parts.append("환자명 없음")

        return round(score, 4), parts
