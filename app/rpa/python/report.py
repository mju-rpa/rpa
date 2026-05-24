from datetime import datetime
from pathlib import Path


def format_report(analysis: dict, risk: dict) -> str:
    lines = [
        "======================================",
        "[Atlas 메디케어] 맞춤형 진료/복약 리포트",
        f"발행일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "======================================",
        f"👤 환자명: {analysis.get('환자명')}",
        "",
        "📋 [진료 요약]",
        analysis.get("진료요약", ""),
        "",
        "💊 [복약 스케줄]",
    ]
    for med in analysis.get("필수복약리스트", []):
        lines.append(
            f" - {med.get('약품명')} | {med.get('복용시간')} | 주의: {med.get('주의사항')}"
        )
    lines.extend(
        [
            "",
            "⚠️ [특별 주의사항]",
            analysis.get("상호작용_경고", ""),
            "",
            f"📊 [복약 위험도 점수] {risk.get('최종점수')} / 100",
            f"   재검토 필요: {'예' if risk.get('재검토_필요') else '아니오'}",
            "======================================",
        ]
    )
    return "\n".join(lines)


def save_report_file(analysis: dict, report_text: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = analysis.get("환자명", "patient").replace(" ", "_")
    report_path = output_dir / f"{safe_name}_복약리포트.txt"
    report_path.write_text(report_text, encoding="utf-8")
    return report_path
