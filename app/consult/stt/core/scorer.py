import logging
from app.consult.ocr.api.schema.schema import ConfidenceResult
from app.consult.stt.core.transcriber import TranscriptionResult

logger = logging.getLogger(__name__)

_MEDICAL_KEYWORDS = {
    "처방", "복용", "캡슐", "식후", "식전", "취침전",
    "타이레놀", "항생제", "소화제", "진통제", "아목시실린", "부작용",
    "복약", "1일", "1정", "2정", "2회", "3회", "mg", "주의사항",
}


class SttScorer:
    def score(self, result: TranscriptionResult, llm_score: float) -> ConfidenceResult:
        rule_score, low_fields = self._rule_score(result)
        final = round(llm_score * 0.5 + rule_score * 0.5, 4)
        logger.debug("[SttScorer] llm=%.2f rule=%.2f final=%.2f low=%s",
                     llm_score, rule_score, final, low_fields)
        return ConfidenceResult(
            llm_score=llm_score,
            rule_score=rule_score,
            final=final,
            low_fields=low_fields,
        )

    def _rule_score(self, result: TranscriptionResult) -> tuple[float, list[str]]:
        score = 0.0
        low: list[str] = []
        text = result.text.strip()

        if len(text) > 20:
            score += 0.4
        else:
            low.append("text_length")

        has_keyword = any(kw in text for kw in _MEDICAL_KEYWORDS)
        if has_keyword:
            score += 0.4
        else:
            low.append("medical_keywords")

        if result.duration > 0:
            density = len(text) / result.duration
            if 2.0 <= density <= 30.0:
                score += 0.2
            else:
                low.append("text_density")
        else:
            low.append("text_density")

        return round(score, 4), low
