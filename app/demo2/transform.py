"""consult API 응답 → Agentic/리포트용 텍스트 (input_process 와 동일 규칙)."""
from app.consult.ocr.api.schema.schema import OcrResponse
from app.consult.stt.api.schema.schema import TranscribeResponse


def ocr_to_natural(result: OcrResponse) -> str:
    lines = []
    if result.patient_name:
        lines.append(f"환자명: {result.patient_name}")
    if result.prescribed_date:
        lines.append(f"처방일자: {result.prescribed_date}")
    if result.hospital_name:
        lines.append(f"병원명: {result.hospital_name}")
    for i, m in enumerate(result.medicines, start=1):
        parts = [p for p in [m.dosage, m.frequency, m.timing] if p]
        detail = " ".join(parts)
        line = f"약품 {i}: {m.name}"
        if detail:
            line += f" - {detail}"
        if m.caution:
            line += f"  ※ {m.caution}"
        lines.append(line)
    if result.general_caution:
        lines.append(f"일반주의사항: {result.general_caution}")
    return "\n".join(lines)


def stt_to_dialogue(stt: TranscribeResponse) -> str:
    if stt.segments:
        return "\n".join(f"{s.speaker}: {s.text}" for s in stt.segments)
    return stt.text
