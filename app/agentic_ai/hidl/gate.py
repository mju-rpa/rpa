"""
Human-In-The-Loop (HIDL) 게이트 — 미구현(스텁).

To-Be: 위험도·재검토 플래그 시 담당자 UI에서 승인/거부 후 파이프라인 재개.
데모: AnalyzeRequest.hidl_enabled / hidl_approved 로 시뮬레이션.
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class HidlDecision:
    applied: bool
    status: str  # skipped | pending | approved | rejected
    message: str
    should_continue: bool


def apply_hidl_gate(
    *,
    hidl_enabled: bool,
    hidl_approved: bool | None,
    risk: dict,
    analysis: dict,
) -> HidlDecision:
    """
  Pseudo-code (UiPath / 웹 UI 연동 시):

  if not hidl_enabled:
      return skip

  if risk["재검토_필요"] or risk["최종점수"] < THRESHOLD:
      # POST /hidl/review — 담당자 대시보드에 큐 적재
      # await human decision → hidl_approved True/False
      if hidl_approved is None:
          return pending  # 파이프라인 일시 중지 또는 비동기 job

      if hidl_approved is False:
          return rejected  # RPA: 담당자 알림만, 환자 알림 스킵

  return approved → Self-Reflection 이후 단계 계속
    """
    if not hidl_enabled:
        return HidlDecision(
            applied=False,
            status="skipped",
            message="HIDL 비활성 — 자동 진행",
            should_continue=True,
        )

    needs_human = risk.get("재검토_필요") or risk.get("최종점수", 100) < 70
    patient = analysis.get("환자명", "환자")

    if not needs_human:
        return HidlDecision(
            applied=True,
            status="auto_approved",
            message=f"[HIDL] {patient}: 위험도 기준 이하 — 자동 승인",
            should_continue=True,
        )

    if hidl_approved is None:
        return HidlDecision(
            applied=True,
            status="pending",
            message=(
                f"[HIDL] {patient}: 재검토 필요 — 담당자 승인 대기 "
                "(hidl_approved=null)"
            ),
            should_continue=False,
        )

    if hidl_approved is False:
        return HidlDecision(
            applied=True,
            status="rejected",
            message=f"[HIDL] {patient}: 담당자 거부 — 환자 알림·리포트 중단",
            should_continue=False,
        )

    return HidlDecision(
        applied=True,
        status="approved",
        message=f"[HIDL] {patient}: 담당자 승인 — 파이프라인 계속",
        should_continue=True,
    )


def hidl_trace_entry(decision: HidlDecision) -> dict[str, Any]:
    return {
        "step": 9,
        "role": "HIDL",
        "agent": "Human Review Gate",
        "action": f"HIDL {decision.status}",
        "detail": decision.message,
    }
