# -*- coding: utf-8 -*-
"""
보고서 생성 모듈
Agentic AI 분석 결과를 받아 환자 맞춤형 복약 보고서를 생성합니다.
"""

from datetime import datetime
from pathlib import Path


def generate_medication_report(analysis: dict, risk_score: dict, patient_info: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    patient_name = analysis.get("환자명", "알 수 없음")
    summary = analysis.get("진료요약", "정보 없음")
    med_list = analysis.get("필수복약리스트", [])
    interaction = analysis.get("상호작용_경고", "없음")
    final_score = risk_score.get("최종점수", 0)
    needs_review = risk_score.get("재검토_필요", False)
    deductions = risk_score.get("감점항목", [])
    alert_type = patient_info.get("알림매체", "none")
    phone = patient_info.get("연락처", {}).get("전화번호", "미등록")

    report = []
    report.append("=" * 50)
    report.append("[Atlas 메디케어] 맞춤형 복약 안내 보고서")
    report.append("발행일시: " + now)
    report.append("=" * 50)

    report.append("")
    report.append("[환자 기본 정보]")
    report.append("  - 환자명     : " + patient_name)
    report.append("  - 연락처     : " + phone)
    report.append("  - 알림 수단  : " + alert_type)

    report.append("")
    report.append("[진료 요약]")
    report.append("  " + summary)

    report.append("")
    report.append("[복약 스케줄 상세]")
    if med_list:
        for i, med in enumerate(med_list, 1):
            name = med.get("약품명", "알 수 없음")
            timing = med.get("복용시간", "알 수 없음")
            caution = med.get("주의사항", "없음")
            report.append("  [" + str(i) + "] " + name)
            report.append("      복용시간 : " + timing)
            report.append("      주의사항 : " + caution)
    else:
        report.append("  복약 정보 없음")

    report.append("")
    report.append("[약물 상호작용 경고]")
    if interaction and interaction != "없음":
        report.append("  주의! " + interaction)
    else:
        report.append("  특별한 상호작용 경고 없음")

    report.append("")
    report.append("[복약 시 꼭 지켜주세요]")
    report.append("  - 처방된 용량과 횟수를 반드시 지켜주세요")
    report.append("  - 임의로 복용을 중단하지 마세요")
    report.append("  - 다른 약과 함께 복용 시 의사/약사에게 문의하세요")
    report.append("  - 부작용 발생 시 즉시 의료진에게 알려주세요")
    report.append("  - 음주는 대부분의 약물과 상호작용이 있으니 주의하세요")

    report.append("")
    report.append("[복약 위험도 평가]")
    report.append("  최종 점수 : " + str(final_score) + " / 100점")

    if deductions:
        report.append("  감점 항목 :")
        for d in deductions:
            report.append("    - " + d.get("항목", "") + " : -" + str(d.get("감점", 0)) + "점")

    if needs_review:
        report.append("")
        report.append("  [재검토 필요] 위험도 점수가 기준(70점) 미만입니다.")
        report.append("  담당자에게 재검토 요청이 전송됩니다.")
    else:
        report.append("")
        report.append("  [정상] 환자 알림 채널로 안내문이 발송됩니다.")

    report.append("")
    report.append("[다음 진료 안내]")
    report.append("  증상이 호전되지 않거나 부작용이 생기면")
    report.append("  즉시 담당 의사에게 연락하세요.")

    report.append("")
    report.append("=" * 50)
    report.append("  본 보고서는 Atlas 메디케어 자동화 시스템에서")
    report.append("  자동 생성된 문서입니다.")
    report.append("=" * 50)

    return "\n".join(report)


def save_report(report_text: str, patient_name: str, output_dir: str = "./output") -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    file_name = patient_name + "_복약보고서_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
    file_path = output_path / file_name
    file_path.write_text(report_text, encoding="utf-8")
    print("보고서 저장 완료: " + str(file_path))
    return str(file_path)


def check_risk_and_flag(risk_score: dict) -> str:
    final_score = risk_score.get("최종점수", 0)
    needs_review = risk_score.get("재검토_필요", False)
    reason = risk_score.get("재검토_사유", "")

    if needs_review:
        return "[담당자 알림] 위험도 " + str(final_score) + "점 - 재검토 필요\n사유: " + reason
    elif final_score >= 90:
        return "[정상] 위험도 " + str(final_score) + "점 - 환자 알림 발송"
    else:
        return "[주의] 위험도 " + str(final_score) + "점 - 확인 권장"


if __name__ == "__main__":
    sample_analysis = {
        "환자명": "홍길동",
        "진료요약": "고혈압 및 당뇨 복합 처방",
        "필수복약리스트": [
            {"약품명": "메트포르민 (당뇨약)", "복용시간": "아침 식후 30분", "주의사항": "알코올 섭취 금지"},
            {"약품명": "암로디핀 (혈압약)", "복용시간": "저녁 식후", "주의사항": "자몽주스 섭취 금지"}
        ],
        "상호작용_경고": "당뇨약과 혈압약 병용 시 저혈당 주의"
    }
    sample_risk = {
        "최종점수": 60,
        "재검토_필요": True,
        "재검토_사유": "위험도 점수 60점이 기준(70점) 미만",
        "감점항목": [
            {"항목": "상호작용 경고", "감점": 30},
            {"항목": "복용 주의 필요", "감점": 10}
        ]
    }
    sample_patient = {
        "알림매체": "google_calendar",
        "연락처": {"전화번호": "010-5678-1234"}
    }

    report = generate_medication_report(sample_analysis, sample_risk, sample_patient)
    print(report)
    save_report(report, "홍길동")
    flag = check_risk_and_flag(sample_risk)
    print(flag)
