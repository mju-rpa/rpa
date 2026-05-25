"""demo2 결과 저장 — output/demo2/"""
import json
from datetime import datetime
from pathlib import Path

from app.demo2.collect import Demo2Result
from app.demo2.log_helper import demo2_log

_OUTPUT = Path(__file__).resolve().parent.parent.parent / "output" / "demo2"


def save_demo2(result: Demo2Result) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = _OUTPUT / f"{ts}_consult_api"
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "ocr_response.json").write_text(
        json.dumps(result.ocr.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (folder / "stt_response.json").write_text(
        json.dumps(result.stt.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (folder / "ocr_natural.txt").write_text(result.ocr_natural, encoding="utf-8")
    (folder / "stt_dialogue.txt").write_text(result.stt_dialogue, encoding="utf-8")

    combined = {
        "meta": {
            "mode": result.mode,
            "base_url": result.base_url,
            "image": str(result.image_path),
            "audio": str(result.audio_path),
            "apis_called": ["POST /ocr/extract", "POST /stt/transcribe"],
            "consult_package_touched": False,
        },
        "ocr": result.ocr.model_dump(),
        "stt": result.stt.model_dump(),
        "for_agentic": {
            "stt_text": result.stt_dialogue,
            "ocr_text": result.ocr_natural,
            "환자명": result.patient_name,
        },
    }
    (folder / "consult_combined.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "output_dir": str(folder),
        "patient_name": result.patient_name,
        "mode": result.mode,
        "base_url": result.base_url,
        "files": [
            "ocr_response.json",
            "stt_response.json",
            "ocr_natural.txt",
            "stt_dialogue.txt",
            "consult_combined.json",
        ],
    }
    (folder / "demo2_result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    demo2_log("SUCCESS", "persist", f"saved {folder}")
    return folder
