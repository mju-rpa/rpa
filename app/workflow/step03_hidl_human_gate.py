"""Stage 4: HIDL (Human-In-The-Loop) — 담당자 승인 게이트."""

from app.agentic_ai.hidl.gate import apply_hidl_gate, hidl_trace_entry
from app.agentic_ai.schema.models import AnalyzeRequest


def hidl_human_gate(req: AnalyzeRequest, analysis: dict, risk: dict) -> dict:
    decision = apply_hidl_gate(
        hidl_enabled=req.hidl_enabled,
        hidl_approved=req.hidl_approved,
        risk=risk,
        analysis=analysis,
    )
    return {
        "decision": decision,
        "trace": hidl_trace_entry(decision),
        "blocked": not decision.should_continue,
    }
