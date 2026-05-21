"""고위험 샘플로 점수·재검토 분기 확인 (UiPath If 테스트용)."""
import json
from pathlib import Path

from app.pipeline import run_pipeline
from app.schemas import AnalyzeRequest

DEMO_ROOT = Path(__file__).resolve().parent
SAMPLE = DEMO_ROOT / "data" / "sample_input_high_risk.json"


def main():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    result = run_pipeline(AnalyzeRequest(**data), DEMO_ROOT / "output")
    risk = result["risk_score"]
    print("=== High Risk Sample ===")
    print(f"Patient: {result['analysis']['환자명']}")
    print(f"Score: {risk['최종점수']} / 100")
    print(f"Needs review: {risk['재검토_필요']}")
    print(f"Reason: {risk.get('재검토_사유', '')}")
    print("\n--- Agent Trace ---")
    for t in result["agent_trace"]:
        print(f"  [{t['step']}] {t['agent']}: {t['action']} -> {t.get('detail', '')}")


if __name__ == "__main__":
    main()
