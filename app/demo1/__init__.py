"""Demo1: consult(OCR·STT) API 호출 → Agentic AI 인계 형식 비교·파이프라인 시연."""

# demo1의 의미
"""
Demo1이 보여주는 것 (결과·과정)
목적: consult → Agentic AI로 넘길 때 자연어 vs JSON 비교 + (선택) 전체 파이프라인

과정 (fixture 기본):

fixtures OCR JSON + input STT 문자열
  → handoff_natural.txt / handoff_json.json
  → analyze_request.json (stt_text, ocr_text)
  → (--pipeline 시) run_pipeline → risk 100점 + 복약리포트.txt + final_report.txt
산출물: output/demo1/{timestamp}_{sample}/

handoff_* — 인계 비교용 (API 원본 아님)
analyze_request.json — Agentic 입력
pipeline_result.json, final_report.txt — --pipeline 시
키가 쓰이는 경우: source=api + --image / --audio (또는 Swagger 업로드) + 서버/CLI가 consult 라우터를 탈 때뿐입니다.

"""