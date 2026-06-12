import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    speaker: str
    text: str
    start: float
    end: float


@dataclass
class TranscriptionResult:
    text: str
    language: str
    duration: float
    segments: list[SpeakerSegment] = field(default_factory=list)


class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, file_path: str) -> TranscriptionResult:
        ...


class WhisperTranscriber(Transcriber):
    _MEDICAL_PROMPT = (
        "처방전, 약봉투, 복용량, 식후 30분, 타이레놀, 아목시실린, "
        "항생제, 소화제, 진통제, 1일 3회, 1정, 복약, 부작용"
    )

    def __init__(self, model_size: str = "medium", language: str = "ko",
                 device: str = "cpu", compute_type: str = "int8"):
        logger.info("WhisperTranscriber 초기화 중 (model=%s, device=%s, compute_type=%s)", model_size, device, compute_type)
        from faster_whisper import WhisperModel
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self._language = language
        logger.info("WhisperTranscriber 초기화 완료")

    def transcribe(self, file_path: str) -> TranscriptionResult:
        logger.info("[WhisperTranscriber] 전사 시작: %s", file_path)
        segments_gen, info = self._model.transcribe(
            file_path,
            language=self._language,
            initial_prompt=self._MEDICAL_PROMPT,
        )
        segments = list(segments_gen)
        text = " ".join(segment.text.strip() for segment in segments)
        logger.info("[WhisperTranscriber] 전사 완료 - 언어=%s, 길이=%.1fs, 텍스트 길이=%d자", info.language, info.duration, len(text))
        logger.debug("[WhisperTranscriber] 결과 텍스트: %s", text)
        return TranscriptionResult(text=text, language=info.language, duration=info.duration)


class OpenAIWhisperTranscriber(Transcriber):
    def __init__(self, api_key: str, language: str = "ko"):
        logger.info("OpenAIWhisperTranscriber 초기화 (language=%s)", language)
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._language = language

    def transcribe(self, file_path: str) -> TranscriptionResult:
        logger.info("[OpenAIWhisperTranscriber] 전사 시작: %s", file_path)
        with open(file_path, "rb") as f:
            response = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=self._language,
                response_format="verbose_json",
            )
        logger.info("[OpenAIWhisperTranscriber] 전사 완료 - 언어=%s, 길이=%.1fs, 텍스트 길이=%d자", response.language, response.duration or 0.0, len(response.text))
        logger.debug("[OpenAIWhisperTranscriber] 결과 텍스트: %s", response.text)
        return TranscriptionResult(
            text=response.text,
            language=response.language,
            duration=response.duration or 0.0,
        )


class ClovaSpeechTranscriber(Transcriber):
    def __init__(self, invoke_url: str, secret_key: str, language: str = "ko-KR",
                 diarization: bool = True, speaker_count_min: int = 2, speaker_count_max: int = 2):
        logger.info("ClovaSpeechTranscriber 초기화 (diarization=%s, speakers=%d~%d)", diarization, speaker_count_min, speaker_count_max)
        import httpx
        self._client = httpx.Client(timeout=600)
        self._invoke_url = invoke_url
        self._secret_key = secret_key
        self._language = language
        self._diarization = diarization
        self._speaker_count_min = speaker_count_min
        self._speaker_count_max = speaker_count_max

    _MIME_MAP = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }

    def transcribe(self, file_path: str) -> TranscriptionResult:
        logger.info("[ClovaSpeechTranscriber] 전사 시작: %s", file_path)
        ext = Path(file_path).suffix.lower()
        mime_type = self._MIME_MAP.get(ext, "audio/mpeg")
        logger.info("[ClovaSpeechTranscriber] MIME 타입: %s", mime_type)

        params = {
            "language": self._language,
            "completion": "sync",
            "diarization": {
                "enable": self._diarization,
                "speakerCountMin": self._speaker_count_min,
                "speakerCountMax": self._speaker_count_max,
            },
        }

        with open(file_path, "rb") as f:
            response = self._client.post(
                f"{self._invoke_url}/recognizer/upload",
                headers={"X-CLOVASPEECH-API-KEY": self._secret_key},
                files={"media": (file_path, f, mime_type)},
                data={"params": __import__("json").dumps(params)},
            )

        response.raise_for_status()
        body = response.json()
        if body.get("result") != "COMPLETED":
            raise RuntimeError(f"Clova STT 실패: result={body.get('result')}, message={body.get('message')}")
        logger.debug("[ClovaSpeechTranscriber] 응답: %s", body)

        segments = self._parse_segments(body)
        text = " ".join(s.text for s in segments) if segments else body.get("text", "")
        duration = body.get("segments", [{}])[-1].get("end", 0) / 1000 if body.get("segments") else 0.0

        speakers = sorted({s.speaker for s in segments})
        logger.info("[ClovaSpeechTranscriber] 전사 완료 - 화자 수=%d(%s), 세그먼트 수=%d, 길이=%.1fs, 텍스트 길이=%d자",
                    len(speakers), ", ".join(speakers), len(segments), duration, len(text))
        for seg in segments:
            logger.info("[ClovaSpeechTranscriber] [%.1fs~%.1fs] %s: %s", seg.start, seg.end, seg.speaker, seg.text)
        logger.debug("[ClovaSpeechTranscriber] 결과 텍스트: %s", text)

        return TranscriptionResult(text=text, language="ko", duration=duration, segments=segments)

    def _parse_segments(self, body: dict) -> list[SpeakerSegment]:
        result = []
        for seg in body.get("segments", []):
            speaker_label = seg.get("diarization", {}).get("label", "Unknown")
            result.append(SpeakerSegment(
                speaker=f"화자{speaker_label}",
                text=seg.get("text", "").strip(),
                start=seg.get("start", 0) / 1000,
                end=seg.get("end", 0) / 1000,
            ))
        return result


class RemoteWhisperTranscriber(Transcriber):
    def __init__(self, server_url: str, language: str = "ko"):
        logger.info("RemoteWhisperTranscriber 초기화 (server_url=%s, language=%s)", server_url, language)
        import httpx
        self._client = httpx.Client(base_url=server_url, timeout=300)
        self._language = language

    def transcribe(self, file_path: str) -> TranscriptionResult:
        logger.info("[RemoteWhisperTranscriber] 전사 시작: %s", file_path)
        with open(file_path, "rb") as f:
            response = self._client.post(
                "/v1/audio/transcriptions",
                files={"file": (file_path, f, "audio/wav")},
                data={"language": self._language},
            )
        response.raise_for_status()
        body = response.json()
        logger.info("[RemoteWhisperTranscriber] 전사 완료 - 텍스트 길이=%d자", len(body["text"]))
        logger.debug("[RemoteWhisperTranscriber] 결과 텍스트: %s", body["text"])
        return TranscriptionResult(text=body["text"], language=self._language, duration=body.get("duration", 0.0))