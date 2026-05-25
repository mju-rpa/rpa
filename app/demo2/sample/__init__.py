"""
Demo2 샘플 미디어 — app/demo2/sample/

이 폴더에 넣을 파일 (기본 이름)
---------------------------------
  pill.jpg   — 약봉투·처방전 사진 (OCR → POST /ocr/extract)
  visit.wav  — 의사·환자 대화 녹음 (STT → POST /stt/transcribe, Clova 화자 구분 권장)

어디서 구할까? (검색·다운로드)
---------------------------------

[1] 팀원 예제 (가장 권장)
  - OCR/STT 작업할 때 썼던 약봉투 사진·진료 녹음을 그대로 복사
  - 파일명만 pill.jpg / visit.wav 로 맞추거나 CLI에서 --image/--audio 지정

[2] 직접 촬영·녹음 (과제·데모용, 개인정보 주의)
  - 이미지: 약국/교육용 모형 약봉투, 팀 공유 샘플 출력물 캡처 (실제 환자 정보 가림)
  - 음성: 휴대폰 녹음 30초~2분, 2인 대화 형식
    예) "의사: 식전에 드세요. 환자: 네 알겠습니다."
  - 저장: visit.wav (또는 .mp3 → ffmpeg 로 wav 변환)

[3] AI-Hub (한국어 의료 음성, 승인 후 다운로드)
  - https://aihub.or.kr — 검색어: "비대면 진료 음성", "응급실 임상 대화", "의료 대화"
  - 데이터셋 페이지 → 샘플(경량) 데이터 또는 승인 후 API 다운로드
  - WAV 16kHz mono 가 Clova·Whisper 와 잘 맞음
  - JSON 전사에서 대화 한 건 골라 해당 wav 만 sample/visit.wav 로 복사

[4] 공개 음성 코퍼스 (의료 아님, STT 연결 테스트만)
  - Mozilla Common Voice 한국어: https://commonvoice.mozilla.org/ko/datasets
  - Openslr Korean speech: http://www.openslr.org/40/ (대용량, 일부만 추출)
  → 진료 시나리오는 아니지만 "API·키 동작 확인" 용도로는 가능

[5] 약봉투 이미지 (OCR 테스트)
  - 팀 발표 자료·가이드에 있는 예시 JPG 캡처
  - 직접 A4에 약품명·복용법 인쇄 후 사진 (가장 재현 쉬움)
  - 검색: "약봉투 처방" + 교육/스톡 (상업 라이선스 확인)

로컬 테스트용 자동 생성 (임시·품질 낮음)
---------------------------------
  프로젝트 루트에서:
    python app/demo2/sample/generate_test_media.py

  - pill.jpg: 한글 처방 텍스트가 그려진 합성 이미지 (Gemini OCR 동작 확인용)
  - visit.wav: 짧은 한국어 TTS 또는 무음 placeholder
  → Clova 화자 구분·진료 품질 검증은 [1]~[3] 실제 파일이 필요합니다.

실행
----
  python -m app.demo2.run_cli --inprocess \\
    --image app/demo2/sample/pill.jpg \\
    --audio app/demo2/sample/visit.wav

주의
----
  - sample/ 파일은 .gitignore 대상일 수 있음 (용량·개인정보). 팀 공유는 별도 채널.
  - consult(app/consult) 코드는 수정하지 않음. Demo2는 HTTP API만 호출합니다.
"""

# 패키지 마커 — 미디어는 이 디렉터리의 pill.jpg, visit.wav (바이너리)
