"""
UiPath 없이 터미널 데모. workflow.run_pipeline 과 동일.
"""
import json
from pathlib import Path

from app.consult_alias import register_consult_import_alias

register_consult_import_alias()

from app.agentic_ai.schema.models import AnalyzeRequest
from app.log.configure import setup_logging
from app.workflow.run_pipeline import run_pipeline

setup_logging()

SAMPLE = Path(__file__).parent / "input" / "sample_input.json"


def main():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    req = AnalyzeRequest(**data)
    print("=" * 50)
    print("[step01] collect_convert (input/sample_input.json)")
    print("[step02] agentic + reflection + score")
    print("[step03] hidl (default off)")
    print("[step04] rpa + notification")
    print("=" * 50)

    result = run_pipeline(req, Path(__file__).parent / "output")
    print(result.get("report_text", ""))
    print("\n--- Agent Trace ---")
    for t in result.get("agent_trace", []):
        rev = " [REVISED]" if t.get("revised") else ""
        print(f"  Step {t['step']} | {t['agent']}{rev}")
        print(f"           {t['action']}")
    print("\n--- Risk Score ---")
    print(json.dumps(result.get("risk_score", {}), ensure_ascii=False, indent=2))
    if result.get("report_file"):
        print(f"\n[OK] saved: {result['report_file']}")


if __name__ == "__main__":
    main()
