"""고위험 샘플 + HIDL 분기 확인."""
import json
from pathlib import Path

from app.consult_alias import register_consult_import_alias

register_consult_import_alias()

from app.agentic_ai.schema.models import AnalyzeRequest
from app.workflow.run_pipeline import run_pipeline

DEMO_ROOT = Path(__file__).resolve().parent
SAMPLE = DEMO_ROOT / "input" / "sample_input_high_risk.json"


def main():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    result = run_pipeline(AnalyzeRequest(**data), DEMO_ROOT / "output")
    risk = result["risk_score"]
    print("=== High Risk Sample ===")
    print(f"Workflow: {result.get('workflow_stage')}")
    print(f"Score: {risk['최종점수']} needs_review={risk['재검토_필요']}")


if __name__ == "__main__":
    main()
