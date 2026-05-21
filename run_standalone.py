"""
UiPath 없이 터미널에서만 데모 실행.
API 서버와 동일한 pipeline 사용.
"""
import json
from pathlib import Path

from app.pipeline import run_pipeline
from app.schemas import AnalyzeRequest

SAMPLE = Path(__file__).parent / "data" / "sample_input.json"


def main():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    req = AnalyzeRequest(**data)
    print("=" * 50)
    print("[Step 1] RPA collect - STT/OCR (to_be_generated, now: sample_input.json)")
    print("[Step 2] Agentic AI analyze + Self-Reflection")
    print("[Step 3] Risk score + notification plan")
    print("[Step 4] RPA report file")
    print("=" * 50)

    result = run_pipeline(req, Path(__file__).parent / "output")
    print(result["report_text"])
    print("\n--- Agent Trace (show this to team) ---")
    for t in result.get("agent_trace", []):
        rev = " [REVISED]" if t.get("revised") else ""
        print(f"  Step {t['step']} | {t['agent']}{rev}")
        print(f"           {t['action']}")
        print(f"           -> {t.get('detail', '')}")
    print("\n--- Reflection ---")
    for log in result["reflection_logs"]:
        print(f"  Round {log['round']}: {log['critic_feedback']} (수정: {log['revised']})")
    print("\n--- Risk Score ---")
    print(json.dumps(result["risk_score"], ensure_ascii=False, indent=2))
    print("\n--- RPA Actions ---")
    for action in result["rpa_actions"]:
        print(f"  {action}")
    print(f"\n[OK] saved: {result['report_file']}")


if __name__ == "__main__":
    main()
