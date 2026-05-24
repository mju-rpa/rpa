Python 3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
"""
보고서 생성 모듈 (담당: 아영)
Agentic AI 분석 결과를 받아 환자 맞춤형 복약 보고서를 생성합니다.
"""

from datetime import datetime
from pathlib import Path
import json


def generate_medication_report(analysis: dict, risk_score: dict, patient_info: dict) -> str:
    """
    Agentic AI 분석 결과를 바탕으로 환자 맞춤형 복약 보고서를 생성합니다.
    
    Args:
        analysis: Agentic AI 분석 결과
        risk_score: 위험도 점수 정보
        patient_info: 환자 기본 정보
    
    Returns:
        보고서 텍스트
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    환자명 = analysis.get("환자명", "알 수 없음")
    진료요약 = analysis.get("진료요약", "정보 없음")
    복약리스트 = analysis.get("필수복약리스트", [])
    상호작용경고 = analysis.get("상호작용_경고", "없음")
    최종점수 = risk_score.get("최종점수", 0)
    재검토필요 = risk_score.get("재검토_필요", False)
    감점항목 = risk_score.get("감점항목", [])
    알림매체 = patient_info.get("알림매체", "none")
    전화번호 = patient_info.get("연락처", {}).get("전화번호", "미등록")

    report = []
    report.append("=" * 50)
    report.append("🏥 [Atlas 메디케어] 맞춤형 복약 안내 보고서")
    report.append(f"📅 발행일시: {now}")
    report.append("=" * 50)

    # 환자 기본 정보
    report.append("")
    report.append("▶ 환자 기본 정보")
    report.append(f"  - 환자명     : {환자명}")
    report.append(f"  - 연락처     : {전화번호}")
    report.append(f"  - 알림 수단  : {알림매체}")

    # 진료 요약
    report.append("")
    report.append("▶ 진료 요약")
    report.append(f"  {진료요약}")

    # 복약 스케줄 상세
    report.append("")
    report.append("▶ 복약 스케줄 상세")
    if 복약리스트:
        for i, 약 in enumerate(복약리스트, 1):
            약품명 = 약.get("약품명", "알 수 없음")
            복용시간 = 약.get("복용시간", "알 수 없음")
            주의사항 = 약.get("주의사항", "없음")
            report.append(f"  [{i}] {약품명}")
            report.append(f"      복용시간 : {복용시간}")
            report.append(f"      주의사항 : {주의사항}")
    else:
        report.append("  복약 정보 없음")

    # 약물 상호작용 경고
    report.append("")
    report.append("▶ 약물 상호작용 경고")
    if 상호작용경고 and 상호작용경고 != "없음":
        report.append(f"  ⚠️  {상호작용경고}")
    else:
        report.append("  ✅ 특별한 상호작용 경고 없음")

    # 복약 시 주의사항 체크리스트
    report.append("")
    report.append("▶ 복약 시 꼭 지켜주세요!")
    report.append("  □ 처방된 용량과 횟수를 반드시 지켜주세요")
    report.append("  □ 임의로 복용을 중단하지 마세요")
    report.append("  □ 다른 약과 함께 복용 시 의사/약사에게 문의하세요")
    report.append("  □ 부작용 발생 시 즉시 의료진에게 알려주세요")
    report.append("  □ 음주는 대부분의 약물과 상호작용이 있으니 주의하세요")

    # 위험도 평가
    report.append("")
    report.append("▶ 복약 위험도 평가")
    report.append(f"  최종 점수 : {최종점수} / 100점")

    if 감점항목:
        report.append("  감점 항목 :")
        for 항목 in 감점항목:
            report.append(f"    - {항목.get('항목', '')} : -{항목.get('감점', 0)}점")

    if 재검토필요:
        report.append("")
        report.append("  🔴 담당 의료진 재검토 필요")
        report.append("     → 위험도 점수가 기준(70점) 미만입니다.")
        report.append("     → 담당자에게 재검토 요청이 전송됩니다.")
    else:
        report.append("")
        report.append("  🟢 정상 범위")
        report.append("     → 환자 알림 채널로 안내문이 발송됩니다.")

    # 다음 진료 안내
    report.append("")
    report.append("▶ 다음 진료 안내")
    report.append("  증상이 호전되지 않거나 부작용이 생기면")
    report.append("  즉시 담당 의사에게 연락하세요.")

    report.append("")
...     report.append("=" * 50)
...     report.append("  본 보고서는 Atlas 메디케어 자동화 시스템에서")
...     report.append("  자동 생성된 문서입니다.")
...     report.append("=" * 50)
... 
...     return "\n".join(report)
... 
... 
... def save_report(report_text: str, 환자명: str, output_dir: str = "./output") -> str:
...     """
...     생성된 보고서를 파일로 저장합니다.
...     
...     Args:
...         report_text: 보고서 텍스트
...         환자명: 환자 이름
...         output_dir: 저장 경로
...     
...     Returns:
...         저장된 파일 경로
...     """
...     output_path = Path(output_dir)
...     output_path.mkdir(parents=True, exist_ok=True)
... 
...     file_name = f"{환자명}_복약보고서_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
...     file_path = output_path / file_name
... 
...     file_path.write_text(report_text, encoding="utf-8")
...     print(f"✅ 보고서 저장 완료: {file_path}")
...     return str(file_path)
... 
... 
... def check_risk_and_flag(risk_score: dict) -> str:
...     """
...     위험도 점수를 확인하고 담당자 플래그 메시지를 반환합니다.
...     
...     Args:
...         risk_score: 위험도 점수 정보
...     
    Returns:
        플래그 메시지
    """
    최종점수 = risk_score.get("최종점수", 0)
    재검토필요 = risk_score.get("재검토_필요", False)
    재검토사유 = risk_score.get("재검토_사유", "")

    if 재검토필요:
        return f"🔴 [담당자 알림] 위험도 {최종점수}점 - 재검토 필요\n사유: {재검토사유}"
    elif 최종점수 >= 90:
        return f"🟢 [정상] 위험도 {최종점수}점 - 환자 알림 발송"
    else:
        return f"🟡 [주의] 위험도 {최종점수}점 - 확인 권장"


# 테스트 실행
if __name__ == "__main__":
    # 테스트용 샘플 데이터
    sample_analysis = {
        "환자명": "홍길동",
        "진료요약": "고혈압 및 당뇨 복합 처방",
        "필수복약리스트": [
            {
                "약품명": "메트포르민 (당뇨약)",
                "복용시간": "아침 식후 30분",
                "주의사항": "알코올 섭취 금지"
            },
            {
                "약품명": "암로디핀 (혈압약)",
                "복용시간": "저녁 식후",
                "주의사항": "자몽주스 섭취 금지"
            }
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
        "연락처": {
            "전화번호": "010-5678-1234"
        }
    }

    # 보고서 생성
    report = generate_medication_report(sample_analysis, sample_risk, sample_patient)
    print(report)

    # 파일 저장
    save_report(report, "홍길동")

    # 위험도 플래그 확인
    flag = check_risk_and_flag(sample_risk)
