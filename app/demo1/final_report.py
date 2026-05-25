"""demo1 인계물 + Agentic 파이프라인 결과 → 최종 통합 리포트 텍스트."""
from __future__ import annotations

from typing import Any

from app.demo1.consult_collect import ConsultCollectResult
from app.demo1.handoff import build_handoff_natural


def build_final_report(
    collected: ConsultCollectResult,
    pipeline_result: dict[str, Any] | None,
) -> str:
    """
    consult → agentic → report_generator(format_report) 결과를 한 파일로 합칩니다.
    pipeline_result 가 있으면 step04 의 report_text 가 최종 복약리포트 본문입니다.
    """
    sections = [
        "=" * 50,
        "[Atlas Demo1] 통합 실행 리포트",
        f"sample={collected.sample} source={collected.source}",
        "=" * 50,
        "",
        "── 1. Consult 인계 (자연어 요약) ──",
        build_handoff_natural(collected),
    ]

    if not pipeline_result:
        sections.extend(
            [
                "",
                "── 2. Agentic AI / 최종 복약리포트 ──",
                "(미실행 — --pipeline 또는 POST /demo1/pipeline 사용)",
            ]
        )
        return "\n".join(sections)

    analysis = pipeline_result.get("analysis") or {}
    risk = pipeline_result.get("risk_score") or {}
    sections.extend(
        [
            "",
            "── 2. Agentic AI 분석 요약 ──",
            f"workflow_stage: {pipeline_result.get('workflow_stage', '')}",
            f"환자명: {analysis.get('환자명', collected.patient_name)}",
            f"진료요약: {analysis.get('진료요약', '')}",
            f"상호작용_경고: {analysis.get('상호작용_경고', '')}",
            "",
            "── 3. 복약 위험도 (100점 만점) ──",
            f"기본점수: {risk.get('기본점수', 100)}",
            f"최종점수: {risk.get('최종점수', '—')}",
            f"재검토_필요: {risk.get('재검토_필요', False)}",
        ]
    )
    for d in risk.get("감점항목") or []:
        sections.append(f"  - 감점: {d.get('항목')} ({d.get('감점')}점)")

    report_text = pipeline_result.get("report_text") or ""
    report_file = pipeline_result.get("report_file") or ""
    sections.extend(
        [
            "",
            "── 4. 최종 복약리포트 (report_generator / step04) ──",
            report_text or "(report_text 없음 — HIDL pending 등 확인)",
        ]
    )
    if report_file:
        sections.append(f"\n[저장 경로] {report_file}")

    return "\n".join(sections)
