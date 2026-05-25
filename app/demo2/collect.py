"""Demo2 수집 — consult OCR·STT API 필수, fixture 대체 없음."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.consult.ocr.api.schema.schema import OcrResponse
from app.consult.stt.api.schema.schema import TranscribeResponse
from app.demo2.consult_http import Mode, call_consult_parallel, resolve_base_url
from app.demo2.log_helper import demo2_log
from app.demo2.transform import ocr_to_natural, stt_to_dialogue

_SAMPLE_DIR = Path(__file__).resolve().parent / "sample"
_DEFAULT_IMAGE = _SAMPLE_DIR / "pill.jpg"
_DEFAULT_AUDIO = _SAMPLE_DIR / "visit.wav"


@dataclass
class Demo2Result:
    image_path: Path
    audio_path: Path
    mode: Mode
    base_url: str
    ocr: OcrResponse
    stt: TranscribeResponse
    ocr_natural: str
    stt_dialogue: str
    patient_name: str


def _require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(
            f"{label} 파일이 없습니다: {path}\n"
            f"  → app/demo2/sample/ 에 pill.jpg·visit.wav 를 넣거나\n"
            f"     python app/demo2/sample/generate_test_media.py 로 임시 생성\n"
            f"     (자세한 구하는 법: app/demo2/sample/__init__.py)"
        )
    return path


def resolve_media_paths(image: Path | None, audio: Path | None) -> tuple[Path, Path]:
    img = _require_file(image or _DEFAULT_IMAGE, "OCR 이미지")
    aud = _require_file(audio or _DEFAULT_AUDIO, "STT 음성")
    return img, aud


def run_demo2_consult(
    *,
    image: Path | None = None,
    audio: Path | None = None,
    mode: Mode = "http",
    base_url: str | None = None,
) -> Demo2Result:
    image_path, audio_path = resolve_media_paths(image, audio)
    resolved = resolve_base_url(mode, base_url)

    demo2_log(
        "SUCCESS",
        "collect",
        f"start image={image_path.name} audio={audio_path.name} mode={mode}",
    )

    if mode == "http" and resolved == "inprocess":
        raise ValueError("mode=http 인데 base_url 이 비었습니다.")

    ocr, stt = call_consult_parallel(
        image_path,
        audio_path,
        mode=mode,
        base_url=resolved if mode == "http" else "",
    )
    ocr_natural = ocr_to_natural(ocr)
    stt_dialogue = stt_to_dialogue(stt)
    patient = ocr.patient_name or ""

    demo2_log("SUCCESS", "collect", f"done patient={patient}")
    return Demo2Result(
        image_path=image_path,
        audio_path=audio_path,
        mode=mode,
        base_url=resolved,
        ocr=ocr,
        stt=stt,
        ocr_natural=ocr_natural,
        stt_dialogue=stt_dialogue,
        patient_name=patient,
    )
