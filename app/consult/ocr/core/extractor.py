import json
import logging
from abc import ABC, abstractmethod

from app.ocr.schema.models import Medicine, OcrResponse

logger = logging.getLogger(__name__)

_PROMPT = """
이 이미지는 한국 약봉투입니다. 이미지에서 다음 정보를 추출하여 JSON으로만 응답하세요.
다른 텍스트 없이 JSON만 반환하세요.

스키마:
{
  "patient_name": "환자 이름 (없으면 null)",
  "prescribed_date": "처방일 YYYY-MM-DD 형식 (없으면 null)",
  "hospital_name": "병원/약국명 (없으면 null)",
  "medicines": [
    {
      "name": "약품명",
      "dosage": "1회 복용량 (없으면 null)",
      "frequency": "1일 복용 횟수 (없으면 null)",
      "timing": "복용 시기 예: 식후 30분 (없으면 null)",
      "caution": "해당 약 주의사항 (없으면 null)"
    }
  ],
  "general_caution": "전체 공통 주의사항 (없으면 null)"
}
"""


class Extractor(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str) -> OcrResponse:
        ...


class GeminiExtractor(Extractor):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        logger.info("GeminiExtractor 초기화 (model=%s)", model)
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract(self, image_bytes: bytes, mime_type: str) -> OcrResponse:
        logger.info("[GeminiExtractor] OCR 시작 - 이미지 크기: %d bytes", len(image_bytes))
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                _PROMPT,
            ],
        )

        raw = response.text.strip()
        logger.debug("[GeminiExtractor] 원본 응답: %s", raw)

        # ```json ... ``` 마크다운 블록 제거
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(raw)
        medicines = [Medicine(**m) for m in data.get("medicines", [])]
        result = OcrResponse(
            patient_name=data.get("patient_name"),
            prescribed_date=data.get("prescribed_date"),
            hospital_name=data.get("hospital_name"),
            medicines=medicines,
            general_caution=data.get("general_caution"),
        )
        logger.info("[GeminiExtractor] OCR 완료 - 약품 수: %d", len(medicines))
        return result
