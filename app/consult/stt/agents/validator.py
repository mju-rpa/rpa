import json
import logging

logger = logging.getLogger(__name__)

_PROMPT = """다음은 음성-텍스트 변환(STT) 결과입니다.
이 내용이 약 복용 방법, 처방, 또는 의사-환자 상담에 관한 내용인지 판단하세요.

전사 텍스트:
{text}

JSON으로만 응답하세요 (다른 텍스트 없이):
{{"score": 0.0, "reason": "점수 판단 근거를 한 문장으로"}}

score 기준 (0.0~1.0):
- 1.0: 약 복용 방법·처방·의사-환자 의료 상담 내용
- 0.5: 의료와 관련 있으나 직접적인 상담 여부 불확실
- 0.0: 의료 상담과 무관한 내용 (교육, 토론, 일상 대화 등)
"""


class SttLLMValidator:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def validate(self, text: str) -> tuple[float, str]:
        if not text.strip():
            return 0.0, "전사 텍스트 없음"
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": _PROMPT.format(text=text)}],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            logger.info("[SttLLMValidator] LLM 검증 응답: %s", raw)
            data = json.loads(raw)
            score = max(0.0, min(1.0, float(data.get("score", 0.5))))
            reason = data.get("reason", "")
            return score, reason
        except Exception as e:
            logger.warning("[SttLLMValidator] 검증 실패, 0.5 기본값 사용: %s", e)
            return 0.5, "LLM 검증 실패"
