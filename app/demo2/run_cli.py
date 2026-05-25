"""
Demo2 CLI — consult OCR/STT API 전용 (키·미디어 파일 필수).

[방법 A] 서버 먼저 띄운 뒤 HTTP (팀원 API 그대로):
  터미널1: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  터미널2: python -m app.demo2.run_cli --image app/demo2/sample/pill.jpg --audio app/demo2/sample/visit.wav

[방법 B] 한 번에 (in-process TestClient, .env 키 사용):
  python -m app.demo2.run_cli --inprocess --image ... --audio ...

[방법 C] Render:
  python -m app.demo2.run_cli --base-url https://mju-rpa.onrender.com --image ... --audio ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env", override=True)


def main(argv: list[str] | None = None) -> int:
    from app.log.configure import setup_logging
    from app.demo2.collect import run_demo2_consult
    from app.demo2.persist import save_demo2

    setup_logging()

    p = argparse.ArgumentParser(description="Demo2: consult OCR+STT API only")
    p.add_argument("--image", type=Path, help="약봉투 이미지 (기본: app/demo2/sample/pill.jpg)")
    p.add_argument("--audio", type=Path, help="진료 음성 (기본: app/demo2/sample/visit.wav)")
    p.add_argument(
        "--inprocess",
        action="store_true",
        help="TestClient로 동일 앱 내 /ocr·/stt 호출 (별도 uvicorn 불필요)",
    )
    p.add_argument(
        "--base-url",
        type=str,
        default="",
        help="HTTP 모드 base (기본: DEMO2_BASE_URL 또는 http://127.0.0.1:8000)",
    )
    args = p.parse_args(argv)

    mode = "inprocess" if args.inprocess else "http"
    try:
        result = run_demo2_consult(
            image=args.image,
            audio=args.audio,
            mode=mode,  # type: ignore[arg-type]
            base_url=args.base_url or None,
        )
        out = save_demo2(result)
        print("[demo2] OK - consult API only")
        print(f"  output: {out}")
        print(f"  patient: {result.patient_name}")
        print(f"  OCR medicines: {len(result.ocr.medicines)}")
        print(f"  STT segments: {len(result.stt.segments)}")
        return 0
    except FileNotFoundError as e:
        print(f"[demo2] {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[demo2] FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
