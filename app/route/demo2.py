"""Demo2 HTTP — image+audio 필수, consult /ocr·/stt 만 사용."""
import json
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.demo2.collect import run_demo2_consult
from app.demo2.persist import save_demo2
from app.demo2.log_helper import demo2_log

router = APIRouter(prefix="/demo2", tags=["demo2 (consult API 실연동)"])


@router.post("/run")
async def demo2_run(
    image: UploadFile = File(..., description="약봉투 이미지 (필수)"),
    audio: UploadFile = File(..., description="진료 음성 (필수)"),
):
    """
    팀원 consult API 실호출 데모 (POST /ocr/extract + /stt/transcribe).
    업로드 image·audio 필수 — demo1 fixture 대체 없음.
    """
    if not image.filename or not audio.filename:
        raise HTTPException(status_code=400, detail="image 와 audio 파일 모두 필수입니다")

    tmp = Path(tempfile.mkdtemp(prefix="demo2_"))
    try:
        image_path = tmp / image.filename
        audio_path = tmp / audio.filename
        image_path.write_bytes(await image.read())
        audio_path.write_bytes(await audio.read())

        demo2_log("SUCCESS", "http", f"upload image={image.filename} audio={audio.filename}")
        result = run_demo2_consult(image=image_path, audio=audio_path, mode="inprocess")
        out_dir = save_demo2(result)
        return {
            "output_dir": str(out_dir),
            "patient_name": result.patient_name,
            "apis": ["POST /ocr/extract", "POST /stt/transcribe"],
            "ocr_medicine_count": len(result.ocr.medicines),
            "stt_segment_count": len(result.stt.segments),
            "for_agentic": {
                "stt_text": result.stt_dialogue,
                "ocr_text": result.ocr_natural,
            },
            "ocr_response": result.ocr.model_dump(),
            "stt_response": result.stt.model_dump(),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        demo2_log("ERROR", "http", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
