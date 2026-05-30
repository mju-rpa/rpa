import logging
from app.consult.stt.api.schema.schema import SpeakerSegment, SttPipelineResult, TranscribeResponse
from app.consult.stt.core.transcriber import Transcriber
from app.consult.stt.core.scorer import SttScorer

logger = logging.getLogger(__name__)


class STTPipeline:
    def __init__(
        self,
        transcriber: Transcriber,
        retry_threshold: float = 0.65,
        hitl_threshold: float = 0.5,
    ):
        self._transcriber = transcriber
        self._scorer = SttScorer()
        self._retry_threshold = retry_threshold
        self._hitl_threshold = hitl_threshold

    def run(self, file_path: str) -> SttPipelineResult:
        result = self._transcriber.transcribe(file_path)
        confidence = self._scorer.score(result, llm_score=0.5)
        retried = False

        if confidence.final < self._retry_threshold:
            logger.info("[STTPipeline] 신뢰도 낮음(%.2f) — 재시도", confidence.final)
            result = self._transcriber.transcribe(file_path)
            confidence = self._scorer.score(result, llm_score=0.5)
            retried = True

        status = "hitl_required" if confidence.final < self._hitl_threshold else "ok"
        if status == "hitl_required":
            logger.warning("[STTPipeline] HITL 필요 — 최종 신뢰도: %.2f, low_fields: %s",
                           confidence.final, confidence.low_fields)

        data = TranscribeResponse(
            text=result.text,
            language=result.language,
            duration=result.duration,
            segments=[
                SpeakerSegment(speaker=s.speaker, text=s.text, start=s.start, end=s.end)
                for s in result.segments
            ],
        )

        return SttPipelineResult(status=status, data=data, confidence=confidence, retried=retried)
