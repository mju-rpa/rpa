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
    def score(self, result: TranscriptionResult, llm_score: float, llm_reason: str = "") -> ConfidenceResult:
        rule_score, parts = self._rule_score(result)
        score = round(llm_score * 0.5 + rule_score * 0.5, 4)
        response = " | ".join(parts)
        if llm_reason:
            response += f" | LLM: {llm_reason}"
        logger.debug("[SttScorer] llm=%.2f rule=%.2f score=%.2f", llm_score, rule_score, score)
        return ConfidenceResult(
            llm_score=llm_score,
            rule_score=rule_score,
            score=score,
            response=response,
        )

    def _rule_score(self, result: TranscriptionResult) -> tuple[float, list[str]]:
        score = 0.0
        parts: list[str] = []
        text = result.text.strip()

        if len(text) > 20:
            score += 0.4
            parts.append("텍스트 길이 정상")
        else:
            parts.append("텍스트 너무 짧음")

        has_keyword = any(kw in text for kw in _MEDICAL_KEYWORDS)
        if has_keyword:
            score += 0.4
            parts.append("의료 키워드 확인")
        else:
            parts.append("의료 키워드 없음")

        if result.duration > 0:
            density = len(text) / result.duration
            if 2.0 <= density <= 30.0:
                score += 0.2
                parts.append("텍스트 밀도 정상")
            else:
                parts.append(f"텍스트 밀도 이상({density:.1f} chars/sec)")
        else:
            parts.append("음성 길이 정보 없음")

        return round(score, 4), parts
