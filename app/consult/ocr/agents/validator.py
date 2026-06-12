import json
import logging

from app.consult.ocr.api.schema.schema import DiagnosisResponse, OcrResponse

logger = logging.getLogger(__name__)

_OCR_PROMPT = """다음은 한국 약봉투 OCR 추출 결과입니다.
추출된 정보가 실제 약봉투에서 올바르게 읽힌 유효한 데이터인지 판단하세요.

추출 결과:
{data}

JSON으로만 응답하세요 (다른 텍스트 없이):
{{"score": 0.0, "reason": "점수 판단 근거를 한 문장으로"}}

score 기준 (0.0~1.0):
- 1.0: 약품명·복용법 등 핵심 정보가 명확히 추출됨
- 0.5: 일부 정보가 불완전하거나 불확실
- 0.0: 약봉투 데이터로 볼 수 없음 (약품 없음, 이미지 판독 실패 등)
"""

_DIAGNOSIS_PROMPT = """다음은 한국 진단서 OCR 추출 결과입니다.
추출된 정보가 실제 진단서에서 올바르게 읽힌 유효한 데이터인지 판단하세요.

추출 결과:
{data}

JSON으로만 응답하세요 (다른 텍스트 없이):
{{"score": 0.0, "reason": "점수 판단 근거를 한 문장으로"}}

score 기준 (0.0~1.0):
- 1.0: 진단명·병원명 등 핵심 정보가 명확히 추출됨
- 0.5: 일부 정보가 불완전하거나 불확실
- 0.0: 진단서 데이터로 볼 수 없음 (진단명 없음, 이미지 판독 실패 등)
"""


class OcrLLMValidator:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def validate(self, response: OcrResponse) -> tuple[float, str]:
        data = {
            "patient_name": response.patient_name,
            "prescribed_date": response.prescribed_date,
            "hospital_name": response.hospital_name,
            "medicines": [
                {"name": m.name, "dosage": m.dosage, "frequency": m.frequency, "timing": m.timing}
                for m in response.medicines
            ],
        }
        try:
            res = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": _OCR_PROMPT.format(data=json.dumps(data, ensure_ascii=False))}],
                response_format={"type": "json_object"},
            )
            raw = res.choices[0].message.content.strip()
            logger.info("[OcrLLMValidator] LLM 검증 응답: %s", raw)
            parsed = json.loads(raw)
            score = max(0.0, min(1.0, float(parsed.get("score", 0.5))))
            reason = parsed.get("reason", "")
            return score, reason
        except Exception as e:
            logger.warning("[OcrLLMValidator] 검증 실패, 0.5 기본값 사용: %s", e)
            return 0.5, "LLM 검증 실패"


class DiagnosisLLMValidator:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def validate(self, response: DiagnosisResponse) -> tuple[float, str]:
        data = {
            "patient_name": response.patient_name,
            "diagnosis_name": response.diagnosis_name,
            "hospital_name": response.hospital_name,
            "doctor_name": response.doctor_name,
            "diagnosis_date": response.diagnosis_date,
        }
        try:
            res = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": _DIAGNOSIS_PROMPT.format(data=json.dumps(data, ensure_ascii=False))}],
                response_format={"type": "json_object"},
            )
            raw = res.choices[0].message.content.strip()
            logger.info("[DiagnosisLLMValidator] LLM 검증 응답: %s", raw)
            parsed = json.loads(raw)
            score = max(0.0, min(1.0, float(parsed.get("score", 0.5))))
            reason = parsed.get("reason", "")
            return score, reason
        except Exception as e:
            logger.warning("[DiagnosisLLMValidator] 검증 실패, 0.5 기본값 사용: %s", e)
            return 0.5, "LLM 검증 실패"
