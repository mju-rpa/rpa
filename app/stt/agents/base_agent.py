from abc import ABC, abstractmethod
from stt.core.transcriber import TranscriptionResult


class BaseAgent(ABC):
    """STT 텍스트를 받아 후처리하는 에이전트 베이스."""

    @abstractmethod
    def process(self, transcript: TranscriptionResult) -> dict:
        """transcript를 처리하고 결과를 dict로 반환한다."""
        ...
