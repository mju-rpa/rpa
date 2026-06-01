import json
import logging
from abc import ABC, abstractmethod

from app.consult.ocr.api.schema.schema import ConfidenceResult, DiagnosisResponse, Medicine, OcrResponse

logger = logging.getLogger(__name__)

_PROMPT = """
이 이미지는 한국 약봉투입니다. 이미지에서 다음 정보를 추출하여 JSON으로만 응답하세요.
다른 텍스트 없이 JSON만 반환하세요.

스키마:
{
  "patient_name": "환자 이름 (없으면 null)",
  "patient_name_confidence": 0.0,
  "prescribed_date": "처방일 YYYY-MM-DD 형식 (없으면 null)",
  "prescribed_date_confidence": 0.0,
  "hospital_name": "병원/약국명 (없으면 null)",
  "hospital_name_confidence": 0.0,
  "medicines": [
    {
      "name": "약품명",
      "name_confidence": 0.0,
      "dosage": "1회 복용량 (없으면 null)",
      "dosage_confidence": 0.0,
      "frequency": "1일 복용 횟수 (없으면 null)",
      "frequency_confidence": 0.0,
      "timing": "복용 시기 예: 식후 30분 (없으면 null)",
      "timing_confidence": 0.0,
      "caution": "해당 약 주의사항 (없으면 null)",
      "caution_confidence": 0.0
    }
  ],
  "general_caution": "전체 공통 주의사항 (없으면 null)",
  "general_caution_confidence": 0.0
}

confidence 값은 0.0~1.0 사이 숫자로, 해당 필드를 얼마나 확신하는지 나타냅니다.
"""

_PROMPT_RETRY = _PROMPT + """
\n주의: 이전 시도에서 신뢰도가 낮았습니다. 이미지를 더 주의깊게 읽어주세요.
불확실한 항목도 최선의 추측값을 기입하고 confidence를 낮게 설정하세요.
"""


def _parse_raw(raw: str) -> tuple[OcrResponse, float]:
    """JSON 파싱 → (OcrResponse, llm_score)."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)

    confidence_values = []
    for key in ("patient_name_confidence", "prescribed_date_confidence",
                "hospital_name_confidence", "general_caution_confidence"):
        v = data.get(key)
        if v is not None:
            confidence_values.append(float(v))

    medicines = []
    for m in data.get("medicines", []):
        for mkey in ("name_confidence", "dosage_confidence", "frequency_confidence",
                     "timing_confidence", "caution_confidence"):
            v = m.get(mkey)
            if v is not None:
                confidence_values.append(float(v))
        medicines.append(Medicine(
            name=m.get("name", ""),
            dosage=m.get("dosage"),
            frequency=m.get("frequency"),
            timing=m.get("timing"),
            caution=m.get("caution"),
        ))

    llm_score = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5

    result = OcrResponse(
        patient_name=data.get("patient_name"),
        prescribed_date=data.get("prescribed_date"),
        hospital_name=data.get("hospital_name"),
        medicines=medicines,
        general_caution=data.get("general_caution"),
    )
    return result, llm_score


class Extractor(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str, retry: bool = False) -> tuple[OcrResponse, float]:
        ...


class GeminiExtractor(Extractor):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        logger.info("GeminiExtractor 초기화 (model=%s)", model)
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract(self, image_bytes: bytes, mime_type: str, retry: bool = False) -> tuple[OcrResponse, float]:
        logger.info("[GeminiExtractor] OCR 시작 - 이미지 크기: %d bytes, retry=%s", len(image_bytes), retry)
        from google.genai import types

        prompt = _PROMPT_RETRY if retry else _PROMPT
        response = self._client.models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
        )

        raw = response.text.strip()
        logger.debug("[GeminiExtractor] 원본 응답: %s", raw)
        result, llm_score = _parse_raw(raw)
        logger.info("[GeminiExtractor] OCR 완료 - 약품 수: %d, llm_score: %.2f", len(result.medicines), llm_score)
        return result, llm_score


_DIAGNOSIS_PROMPT = """
이 이미지는 한국 진단서입니다. 이미지에서 다음 정보를 추출하여 JSON으로만 응답하세요.
다른 텍스트 없이 JSON만 반환하세요.

스키마:
{
  "patient_name": "환자 이름 (없으면 null)",
  "patient_name_confidence": 0.0,
  "birth_date": "생년월일 YYYY-MM-DD 형식 (없으면 null)",
  "birth_date_confidence": 0.0,
  "diagnosis_name": "진단명 (없으면 null)",
  "diagnosis_name_confidence": 0.0,
  "hospital_name": "병원명 (없으면 null)",
  "hospital_name_confidence": 0.0,
  "doctor_name": "담당 의사명 (없으면 null)",
  "doctor_name_confidence": 0.0,
  "diagnosis_date": "진단일 YYYY-MM-DD 형식 (없으면 null)",
  "diagnosis_date_confidence": 0.0,
  "department": "진료과 (없으면 null)",
  "department_confidence": 0.0,
  "purpose": "발급 목적 (없으면 null)",
  "purpose_confidence": 0.0
}

confidence 값은 0.0~1.0 사이 숫자로, 해당 필드를 얼마나 확신하는지 나타냅니다.
"""

_DIAGNOSIS_PROMPT_RETRY = _DIAGNOSIS_PROMPT + """
\n주의: 이전 시도에서 신뢰도가 낮았습니다. 이미지를 더 주의깊게 읽어주세요.
불확실한 항목도 최선의 추측값을 기입하고 confidence를 낮게 설정하세요.
"""

_DIAGNOSIS_FIELDS = (
    "patient_name_confidence", "birth_date_confidence", "diagnosis_name_confidence",
    "hospital_name_confidence", "doctor_name_confidence", "diagnosis_date_confidence",
    "department_confidence", "purpose_confidence",
)


def _parse_diagnosis_raw(raw: str) -> tuple[DiagnosisResponse, float]:
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    data = json.loads(raw)
    confidence_values = [float(data[k]) for k in _DIAGNOSIS_FIELDS if data.get(k) is not None]
    llm_score = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5
    return DiagnosisResponse(
        patient_name=data.get("patient_name"),
        birth_date=data.get("birth_date"),
        diagnosis_name=data.get("diagnosis_name"),
        hospital_name=data.get("hospital_name"),
        doctor_name=data.get("doctor_name"),
        diagnosis_date=data.get("diagnosis_date"),
        department=data.get("department"),
        purpose=data.get("purpose"),
    ), llm_score


class DiagnosisExtractor(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str, retry: bool = False) -> tuple[DiagnosisResponse, float]:
        ...


class GeminiDiagnosisExtractor(DiagnosisExtractor):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        logger.info("GeminiDiagnosisExtractor 초기화 (model=%s)", model)
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract(self, image_bytes: bytes, mime_type: str, retry: bool = False) -> tuple[DiagnosisResponse, float]:
        logger.info("[GeminiDiagnosisExtractor] 진단서 OCR 시작 - %d bytes, retry=%s", len(image_bytes), retry)
        from google.genai import types
        prompt = _DIAGNOSIS_PROMPT_RETRY if retry else _DIAGNOSIS_PROMPT
        response = self._client.models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
        )
        raw = response.text.strip()
        logger.debug("[GeminiDiagnosisExtractor] 원본 응답: %s", raw)
        result, llm_score = _parse_diagnosis_raw(raw)
        logger.info("[GeminiDiagnosisExtractor] 진단서 OCR 완료 - 진단명: %s, llm_score: %.2f", result.diagnosis_name, llm_score)
        return result, llm_score
