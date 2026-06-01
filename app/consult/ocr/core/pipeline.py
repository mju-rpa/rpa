import logging
from app.consult.ocr.api.schema.schema import DiagnosisPipelineResult, OcrPipelineResult
from app.consult.ocr.core.extractor import DiagnosisExtractor, Extractor
from app.consult.ocr.core.scorer import DiagnosisScorer, OcrScorer

logger = logging.getLogger(__name__)


class OCRPipeline:
    def __init__(
        self,
        extractor: Extractor,
        retry_threshold: float = 0.65,
        hitl_threshold: float = 0.5,
    ):
        self._extractor = extractor
        self._scorer = OcrScorer()
        self._retry_threshold = retry_threshold
        self._hitl_threshold = hitl_threshold

    def run(self, image_bytes: bytes, mime_type: str) -> OcrPipelineResult:
        response, llm_score = self._extractor.extract(image_bytes, mime_type, retry=False)
        confidence = self._scorer.score(response, llm_score)
        retried = False

        if confidence.final < self._retry_threshold:
            logger.info("[OCRPipeline] 신뢰도 낮음(%.2f) — 재시도", confidence.final)
            response, llm_score = self._extractor.extract(image_bytes, mime_type, retry=True)
            confidence = self._scorer.score(response, llm_score)
            retried = True

        status = "hitl_required" if confidence.final < self._hitl_threshold else "ok"
        if status == "hitl_required":
            logger.warning("[OCRPipeline] HITL 필요 — 최종 신뢰도: %.2f, low_fields: %s",
                           confidence.final, confidence.low_fields)

        return OcrPipelineResult(status=status, data=response, confidence=confidence, retried=retried)


class DiagnosisPipeline:
    def __init__(
        self,
        extractor: DiagnosisExtractor,
        retry_threshold: float = 0.65,
        hitl_threshold: float = 0.5,
    ):
        self._extractor = extractor
        self._scorer = DiagnosisScorer()
        self._retry_threshold = retry_threshold
        self._hitl_threshold = hitl_threshold

    def run(self, image_bytes: bytes, mime_type: str) -> DiagnosisPipelineResult:
        response, llm_score = self._extractor.extract(image_bytes, mime_type, retry=False)
        confidence = self._scorer.score(response, llm_score)
        retried = False

        if confidence.final < self._retry_threshold:
            logger.info("[DiagnosisPipeline] 신뢰도 낮음(%.2f) — 재시도", confidence.final)
            response, llm_score = self._extractor.extract(image_bytes, mime_type, retry=True)
            confidence = self._scorer.score(response, llm_score)
            retried = True

        status = "hitl_required" if confidence.final < self._hitl_threshold else "ok"
        if status == "hitl_required":
            logger.warning("[DiagnosisPipeline] HITL 필요 — 최종 신뢰도: %.2f, low_fields: %s",
                           confidence.final, confidence.low_fields)

        return DiagnosisPipelineResult(status=status, data=response, confidence=confidence, retried=retried)
