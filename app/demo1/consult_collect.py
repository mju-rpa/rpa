"""app/consult(OCR·STT) 결과 수집 — fixture(샘플) 또는 공개 API 호출."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.consult.ocr.api.schema.schema import OcrResponse
from app.consult.stt.api.schema.schema import TranscribeResponse
from app.demo1.log_helper import demo1_log


def _ocr_to_text(result: OcrResponse) -> str:
    """app/route/input_process._ocr_to_text 와 동일 — consult OCR → 자연어."""
    lines = []
    if result.patient_name:
        lines.append(f"환자명: {result.patient_name}")
    if result.prescribed_date:
        lines.append(f"처방일자: {result.prescribed_date}")
    if result.hospital_name:
        lines.append(f"병원명: {result.hospital_name}")
    for i, m in enumerate(result.medicines, start=1):
        parts = [p for p in [m.dosage, m.frequency, m.timing] if p]
        detail = " ".join(parts)
        line = f"약품 {i}: {m.name}"
        if detail:
            line += f" - {detail}"
        if m.caution:
            line += f"  ※ {m.caution}"
        lines.append(line)
    if result.general_caution:
        lines.append(f"일반주의사항: {result.general_caution}")
    return "\n".join(lines)


SampleName = Literal["normal", "high_risk"]
SourceName = Literal["fixture", "input_json", "api"]

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_INPUT_SAMPLES = {
    "normal": _BASE_DIR / "input" / "sample_input.json",
    "high_risk": _BASE_DIR / "input" / "sample_input_high_risk.json",
}


@dataclass
class SttCollectResult:
    text: str
    language: str
    duration_sec: float
    segments: list[dict]
    source: str


@dataclass
class ConsultCollectResult:
    sample: SampleName
    source: SourceName
    stt: SttCollectResult
    ocr: OcrResponse
    ocr_natural: str
    patient_name: str


def _load_ocr_fixture(sample: SampleName) -> OcrResponse:
    path = _FIXTURE_DIR / f"ocr_{sample}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return OcrResponse(**data)


def _stt_from_transcribe_response(resp: TranscribeResponse, *, source_label: str) -> SttCollectResult:
    segments = [s.model_dump() for s in resp.segments]
    return SttCollectResult(
        text=resp.text,
        language=resp.language,
        duration_sec=resp.duration,
        segments=segments,
        source=source_label,
    )


def _stt_from_input_text(stt_text: str, *, source_label: str) -> SttCollectResult:
    segments: list[dict] = []
    for line in stt_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            speaker, text = line.split(":", 1)
            segments.append({"speaker": speaker.strip(), "text": text.strip()})
        else:
            segments.append({"speaker": "unknown", "text": line})
    return SttCollectResult(
        text=stt_text,
        language="ko",
        duration_sec=0.0,
        segments=segments,
        source=source_label,
    )


def collect_consult_fixture(sample: SampleName = "normal", source: SourceName = "fixture") -> ConsultCollectResult:
    """키 없이 실행: fixtures + input/*.json STT 텍스트."""
    demo1_log("SUCCESS", "collect", f"fixture start sample={sample} source={source}")

    inp_path = _INPUT_SAMPLES[sample]
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    patient = inp.get("환자명", "")

    ocr = _load_ocr_fixture(sample)
    if source == "input_json":
        ocr_natural = inp.get("ocr_text", "") or _ocr_to_text(ocr)
        demo1_log("SUCCESS", "collect/ocr", f"input_json ocr_text len={len(ocr_natural)}")
    else:
        ocr_natural = _ocr_to_text(ocr)
        demo1_log("SUCCESS", "collect/ocr", f"fixture OcrResponse medicines={len(ocr.medicines)}")

    stt = _stt_from_input_text(
        inp.get("stt_text", ""),
        source_label="fixture (input/sample_input*.json stt_text)",
    )
    demo1_log(
        "SUCCESS",
        "collect/stt",
        f"segments={len(stt.segments)} text_len={len(stt.text)}",
    )

    demo1_log("SUCCESS", "collect", f"done patient={patient or ocr.patient_name}")
    return ConsultCollectResult(
        sample=sample,
        source=source,
        stt=stt,
        ocr=ocr,
        ocr_natural=ocr_natural,
        patient_name=patient or (ocr.patient_name or ""),
    )


def collect_consult_api(
    sample: SampleName = "normal",
    *,
    image_path: Path | None = None,
    audio_path: Path | None = None,
) -> ConsultCollectResult:
    """
    POST /ocr/extract, POST /stt/transcribe 호출.
    파일이 없으면 해당 축은 fixture/input 샘플로 대체(부분 실 API 테스트 가능).
    """
    from app.demo1.consult_api import post_ocr_extract, post_stt_transcribe

    demo1_log("SUCCESS", "collect", f"api start sample={sample} image={image_path} audio={audio_path}")

    inp = json.loads(_INPUT_SAMPLES[sample].read_text(encoding="utf-8"))
    patient = inp.get("환자명", "")

    if image_path and image_path.is_file():
        ocr = post_ocr_extract(image_path)
        ocr_natural = _ocr_to_text(ocr)
        ocr_source = "POST /ocr/extract"
    else:
        ocr = _load_ocr_fixture(sample)
        ocr_natural = _ocr_to_text(ocr)
        ocr_source = "fixture (no image upload)"
        demo1_log("WARN", "collect/ocr", "image 없음 — fixture OCR 사용")

    if audio_path and audio_path.is_file():
        stt_resp = post_stt_transcribe(audio_path)
        stt = _stt_from_transcribe_response(stt_resp, source_label="POST /stt/transcribe")
    else:
        stt = _stt_from_input_text(
            inp.get("stt_text", ""),
            source_label="fixture (no audio upload)",
        )
        demo1_log("WARN", "collect/stt", "audio 없음 — input 샘플 STT 텍스트 사용")

    demo1_log(
        "SUCCESS",
        "collect",
        f"api done patient={patient or ocr.patient_name} ocr={ocr_source}",
    )
    return ConsultCollectResult(
        sample=sample,
        source="api",
        stt=stt,
        ocr=ocr,
        ocr_natural=ocr_natural,
        patient_name=patient or (ocr.patient_name or ""),
    )


def collect_consult(
    sample: SampleName = "normal",
    source: SourceName = "fixture",
    *,
    image_path: Path | None = None,
    audio_path: Path | None = None,
) -> ConsultCollectResult:
    if source == "api":
        return collect_consult_api(sample, image_path=image_path, audio_path=audio_path)
    if source not in ("fixture", "input_json"):
        raise ValueError(f"unsupported source: {source}")
    return collect_consult_fixture(sample, source=source)
