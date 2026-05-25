"""
터미널에서 demo1 실행.

  # 로컬 fixture (키 불필요)
  python -m app.demo1.run_cli --sample normal

  # 로컬 + Agentic + 최종 final_report.txt
  python -m app.demo1.run_cli --sample normal --pipeline

  # 로컬 PC → Render API 호출 (로그는 forward 로 Render Logs)
  python -m app.demo1.run_cli --target render --sample normal
  python -m app.demo1.run_cli --target render --pipeline
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env", override=True)


def _setup_logging_for_forward() -> None:
    """RENDER_LOG_FORWARD_ENABLED 시 demo1_log 가 Render /log/ingest 로 전송되도록 설정."""
    from app.log.configure import setup_logging

    setup_logging()


def _run_local(args: argparse.Namespace) -> int:
    from app.demo1.consult_collect import collect_consult
    from app.demo1.handoff import build_analyze_request, build_handoff_natural
    from app.demo1.log_helper import demo1_log
    from app.demo1.persist import save_demo1_run

    demo1_log("SUCCESS", "cli", f"local start sample={args.sample} source={args.source}")
    collected = collect_consult(
        args.sample,
        source=args.source,
        image_path=args.image,
        audio_path=args.audio,
    )
    pipeline_result = None
    if args.pipeline:
        from app.workflow.run_pipeline import run_pipeline

        inp_path = _ROOT / "input" / (
            "sample_input.json" if args.sample == "normal" else "sample_input_high_risk.json"
        )
        inp = json.loads(inp_path.read_text(encoding="utf-8"))
        req = build_analyze_request(
            collected,
            patient_id=inp.get("patient_id", ""),
            환자명=inp.get("환자명", collected.patient_name),
            알림매체=inp.get("알림매체", "none"),
            hidl_enabled=args.sample == "high_risk",
            hidl_approved=None,
        )
        pipeline_result = run_pipeline(req, _ROOT / "output")

    out = save_demo1_run(collected, pipeline_result=pipeline_result)
    print(f"[demo1] output_dir={out}")
    print(build_handoff_natural(collected)[:600])
    print("...")
    return 0


def _run_render(args: argparse.Namespace) -> int:
    from app.demo1.log_helper import demo1_log
    from app.demo1.render_client import (
        post_demo1_collect,
        post_demo1_pipeline,
        save_render_api_snapshot,
    )

    demo1_log("SUCCESS", "cli", f"render target sample={args.sample} pipeline={args.pipeline}")
    if args.pipeline:
        data = post_demo1_pipeline(
            args.sample,
            source=args.source if args.source in ("fixture", "input_json") else "fixture",
            run_agentic=True,
        )
        label = f"{args.sample}_pipeline"
    else:
        data = post_demo1_collect(
            args.sample,
            source=args.source,
            image_path=args.image,
            audio_path=args.audio,
        )
        label = f"{args.sample}_collect"

    snap = save_render_api_snapshot(label, data)
    print(f"[demo1] Render API 응답 저장: {snap}")
    if data.get("output_dir"):
        print(f"[demo1] (Render 서버 측) output_dir={data['output_dir']}")
    pipeline = data.get("pipeline") or {}
    if pipeline.get("report_text"):
        print(pipeline["report_text"][:500])
        print("...")
    elif data.get("handoff_natural_preview"):
        print(str(data["handoff_natural_preview"])[:500])
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Demo1: consult → handoff → (optional) agentic")
    p.add_argument("--target", choices=["local", "render"], default="local")
    p.add_argument("--sample", choices=["normal", "high_risk"], default="normal")
    p.add_argument("--source", choices=["fixture", "input_json", "api"], default="fixture")
    p.add_argument("--image", type=Path, default=None)
    p.add_argument("--audio", type=Path, default=None)
    p.add_argument("--pipeline", action="store_true")
    args = p.parse_args(argv)

    _setup_logging_for_forward()

    try:
        if args.target == "render":
            return _run_render(args)
        return _run_local(args)
    except Exception as exc:
        from app.demo1.log_helper import demo1_log

        demo1_log("ERROR", "cli", str(exc))
        raise


if __name__ == "__main__":
    sys.exit(main())
