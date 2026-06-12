from unittest.mock import MagicMock
import pytest
from app.consult.stt.core.pipeline import STTPipeline
from app.consult.stt.core.transcriber import TranscriptionResult


def _make_result(text="타이레놀 1정 식후 30분 복용하세요. 항생제도 함께 복용해야 합니다.", duration=15.0):
    return TranscriptionResult(text=text, language="ko", duration=duration)


def test_pipeline_ok_high_confidence():
    transcriber = MagicMock()
    transcriber.transcribe.return_value = _make_result()

    pipeline = STTPipeline(transcriber=transcriber, retry_threshold=0.65, hitl_threshold=0.5)
    result = pipeline.run("/tmp/audio.wav")

    assert result.status == "ok"
    assert result.retried is False
    transcriber.transcribe.assert_called_once()


def test_pipeline_hitl_when_always_low():
    transcriber = MagicMock()
    transcriber.transcribe.return_value = _make_result(text="네.", duration=1.0)

    pipeline = STTPipeline(transcriber=transcriber, retry_threshold=0.65, hitl_threshold=0.5)
    result = pipeline.run("/tmp/audio.wav")

    assert result.status == "hitl_required"
    assert result.retried is True
    assert transcriber.transcribe.call_count == 2
