import logging
from app.consult.ocr.api.schema.schema import ConfidenceResult, OcrResponse

logger = logging.getLogger(__name__)


class OcrScorer:
    def score(self, response: OcrResponse, llm_score: float) -> ConfidenceResult:
        rule_score, low_fields = self._rule_score(response)
        final = round(llm_score * 0.5 + rule_score * 0.5, 4)
        logger.debug("[OcrScorer] llm=%.2f rule=%.2f final=%.2f low=%s",
                     llm_score, rule_score, final, low_fields)
        return ConfidenceResult(
            llm_score=llm_score,
            rule_score=rule_score,
            final=final,
            low_fields=low_fields,
        )

    def _rule_score(self, r: OcrResponse) -> tuple[float, list[str]]:
        score = 0.0
        low: list[str] = []

        if r.medicines:
            score += 0.4
        else:
            low.append("medicines")
            return score, low  # 약품 없으면 나머지 점수 무의미

        has_dosage_freq = any(
            m.dosage and m.frequency for m in r.medicines
        )
        if has_dosage_freq:
            score += 0.3
        else:
            low.append("dosage_frequency")

        if r.hospital_name or r.prescribed_date:
            score += 0.2
        else:
            low.append("hospital_or_date")

        if 1 <= len(r.medicines) <= 10:
            score += 0.1
        else:
            low.append("medicines_count")

        return round(score, 4), low
