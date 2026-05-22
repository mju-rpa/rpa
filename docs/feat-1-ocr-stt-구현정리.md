# feat/1-ocr-stt 구현 정리

> **대상 독자:** 팀원 전체 (발표 자료 참고 + API 테스트 가이드 포함)

---

## 1. 개요

이 브랜치는 "의약품 복약지도 자동화 시스템"의 **1단계 데이터 수집** 파트를 담당한다.  
환자의 **약봉투 이미지(OCR)** 와 **음성 녹음(STT)** 을 받아 구조화된 텍스트로 변환하고,  
이후 Agentic AI 분석 단계(`POST /analyze`)에 전달할 `AnalyzeRequest` JSON을 생성한다.

```
[이미지 파일]  →  OCR (Gemini)   ─┐
                                   ├→  /input-process  →  AnalyzeRequest JSON
[음성 파일]   →  STT (선택 가능)  ─┘
```

---

## 2. 전체 흐름도

```
POST /input-process
  ├─ has_image? → _run_ocr(image)
  │     └─ GeminiExtractor.extract(image_bytes, mime_type)
  │           └─ Gemini API (gemini-2.0-flash) → JSON parse → OcrResponse
  │                 └─ _ocr_to_text() → 구조화 텍스트
  │
  ├─ has_audio? → _run_stt(audio)
  │     └─ Transcriber.transcribe(tmp_file)
  │           └─ [local | remote | openai | clova] 중 하나
  │
  ├─ asyncio.gather() → 병렬 실행
  │
  └─ AnalyzeRequest 조합 → _save_results() → output/input_process/{ts}_{id}/
```

---

## 3. OCR 모듈

### 3.1 왜 Gemini를 선택했는가

| 항목 | Gemini 2.0 Flash | GPT-4o Vision | CLOVA OCR | Google Vision API |
|------|-----------------|--------------|-----------|-------------------|
| **가격** | 무료 티어 / $0.075/1M tokens | $2.5~10/1M tokens | 건당 과금 (월 무료 5,000건) | $1.5/1,000건 |
| **한국어 약봉투** | ✅ 우수 (멀티모달 LLM) | ✅ 우수 | ✅ 우수 (전용 모델) | △ 텍스트 추출만 |
| **구조화 JSON 출력** | ✅ 프롬프트로 직접 제어 | ✅ 프롬프트로 직접 제어 | △ 별도 파싱 필요 | ✗ 텍스트만 반환 |
| **이미지 포맷** | JPEG·PNG·WEBP·HEIC·HEIF | JPEG·PNG·WEBP·GIF | JPEG·PNG | JPEG·PNG·WEBP·GIF |
| **속도** | ~1–2초 | ~2–4초 | ~1–3초 | ~0.5–1초 |
| **약봉투 특화 여부** | △ 범용 (프롬프트로 보완) | △ 범용 | ✅ 의료/영수증 전용 모델 있음 | ✗ 범용 텍스트 |

**선택 이유:**  
- 무료 티어 API가 있어 팀 프로토타이핑 비용이 0원  
- 이미지를 그대로 bytes로 넘겨 멀티모달 추론 → 텍스트 인식 + 의미 이해를 동시에 처리  
- 프롬프트에 JSON 스키마를 직접 명시해 structured output을 강제할 수 있음  
- `gemini-2.0-flash`는 속도와 비용 모두 우수한 경량 모델

### 3.2 코드 경로

```
app/ocr/
├── core/
│   ├── config.py      # GEMINI_API_KEY, GEMINI_MODEL, max_file_size
│   └── extractor.py   # Extractor(ABC) + GeminiExtractor
├── api/
│   ├── schemas.py     # Medicine, OcrResponse (Pydantic)
│   └── router.py      # POST /ocr/extract
└── agents/            # (확장 예정)
```

### 3.3 OCR 프롬프트 전략

`extractor.py`의 `_PROMPT`는 한국 약봉투에 특화된 스키마를 JSON으로 직접 지시한다.

```
약품별: name, dosage, frequency, timing, caution
공통:   patient_name, prescribed_date, hospital_name, general_caution
```

**없는 값은 `null`로 명시** → 모델이 값을 지어내지 않도록 강제한다.

### 3.4 할루시네이션 방어 로직

#### (a) 마크다운 블록 자동 제거
Gemini가 가끔 JSON을 코드 블록으로 감싸 반환할 때:

```python
if raw.startswith("```"):
    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
```

#### (b) Pydantic coerce_to_str validator
모델이 숫자형으로 `dosage`를 반환하는 경우가 있었다 (예: `"dosage": 1` → 문자열 예상).

```python
@field_validator("dosage", "frequency", "timing", "caution", mode="before")
@classmethod
def coerce_to_str(cls, v):
    if v is None:
        return v
    return str(v)
```

#### (c) 파일 크기 사전 차단
20MB 초과 이미지는 API 호출 전 즉시 413 반환 → 무의미한 API 비용 방지.

#### (d) try/except + HTTP 500 래핑 (`/ocr/extract` 전용 라우터)
```python
try:
    result = extractor.extract(contents, _MIME_MAP[ext])
except Exception as e:
    logger.error("OCR 실패: %s", e, exc_info=True)
    raise HTTPException(status_code=500, detail="OCR 처리 중 오류가 발생했습니다")
```

### 3.5 sample-ocr.md (교수님 구현)와 비교

| 항목 | 교수님 구현 (sample-ocr.md) | 이번 구현 |
|------|---------------------------|----------|
| **OCR 엔진** | UiPath ExtendedLanguagesOCR + MachineLearningExtractor (`receipt_24_4_4_2`) | Gemini 2.0 Flash (멀티모달 LLM) |
| **환각 제어** | 정규식으로 허용 외 문자 강제 삭제, 마침표→쉼표 치환, taxonomy.json 스키마 | JSON 스키마 프롬프트 강제, null 명시, coerce validator, 마크다운 파싱 |
| **특화 모델** | 영수증 전용 ML 스킬 (`receipt_24_4_4_2`) | 범용 멀티모달 (약봉투 프롬프트로 보완) |
| **출력 형태** | UiPath DataTable / 변수 | Pydantic 모델 (FastAPI 응답) |
| **실행 환경** | UiPath Studio (로컬 RPA) | Python FastAPI 서버 |
| **구조화 수준** | 규칙 기반 Regex 정규화 | LLM 의미 이해 + 스키마 강제 |

**개선된 점:**
- 약봉투의 *의미*를 이해해서 추출 (복용시기, 주의사항 등 의미 있는 필드 분리)
- 별도 정규식 없이도 정형 JSON 획득
- REST API로 외부 호출 가능 (UiPath에서 HTTP 액티비티로 바로 사용)

**부족한 점:**
- 숫자 데이터 엄격성: 교수님 구현은 금액 같은 수치 데이터에 정규식 2중 방어를 했으나,  
  우리 구현은 복용량(`"1.000 1"` 같은 이상한 값)을 문자열로 그냥 통과시킴
- 영수증 전용 ML 모델 대비 약봉투 인식 정확도는 실제 테스트가 필요함
- 인식 결과 신뢰도(confidence score)가 없어 낮은 품질 이미지 판별 불가

**예외 처리가 이루어진 사례:**
- Gemini가 JSON 앞뒤에 마크다운 펜스(` ```json `) 붙이는 현상 → 파싱 전 제거
- `dosage` 필드가 숫자(`1`)로 반환되는 현상 → `coerce_to_str`로 문자열 강제 변환
- 약품명 누락 시: `medicines: []` 빈 배열 반환 (null 아님)

---

## 4. STT 모듈

### 4.1 STT 모델 선택 비교

| 항목 | Clova Speech | OpenAI Whisper API | Local Whisper (faster-whisper) | Remote Whisper |
|------|-------------|-------------------|-------------------------------|----------------|
| **가격** | 분당 약 ₩8~16 (화자구분 시 더 높음) | $0.006/분 (약 ₩8) | **무료** (로컬 GPU/CPU) | 별도 서버 비용 |
| **한국어 정확도** | ✅ 최상 | △ 양호 | △ 양호 (medium 모델) | medium 모델 수준 |
| **화자 구분 (Diarization)** | ✅ 지원 (speakerCountMin/Max) | ✗ 미지원 | ✗ 미지원 | ✗ 미지원 |
| **속도** | ~10–30초 (서버 처리) | ~5–15초 | CPU: 매우 느림 / GPU: 빠름 | GPU 서버 있으면 빠름 |
| **파일 포맷** | mp3·wav·m4a·ogg·flac | mp3·wav·m4a·ogg·flac·webm | 대부분 포맷 | wav |
| **최대 파일 크기** | 200MB (비동기) | 25MB | 제한 없음 | 제한 없음 |
| **인터넷 필요** | ✅ | ✅ | ✗ (로컬) | ✅ |

**Clova를 기본 권장하는 이유:**
- 약국-환자 대화는 **화자가 2명** → diarization이 있어야 "약사 설명"과 "환자 질문"을 분리할 수 있음
- 한국어 의약품 용어 인식률이 Whisper보다 높음
- 분당 비용이 비싸지만, 복약 지도 대화는 보통 1~3분 이내 → 실제 비용은 ₩10~50 수준

**OpenAI Whisper를 대안으로 쓰는 경우:**
- 화자 구분이 불필요할 때 (단순 텍스트 변환만)
- 비용 최소화 우선, 속도 중시
- 파일이 25MB 이하

**Local Whisper를 사용하지 않은 이유:**
- CPU 환경에서 medium 모델 기준 1분 오디오 처리에 3~10분 소요 → 실시간성 없음
- GPU 없이는 현실적 사용 불가

### 4.2 STT 구현 구조

4가지 Transcriber 구현체가 **Strategy 패턴**으로 교체 가능하게 설계됨:

```python
class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, file_path: str) -> TranscriptionResult: ...

# 구현체 4종
WhisperTranscriber        # 로컬 faster-whisper
OpenAIWhisperTranscriber  # OpenAI Whisper API (whisper-1)
ClovaSpeechTranscriber    # 네이버 Clova Speech (화자 구분 포함)
RemoteWhisperTranscriber  # GPU 서버에 배포된 Whisper
```

`TRANSCRIBER_TYPE` 환경 변수로 런타임에 전환:

```
TRANSCRIBER_TYPE=local   # 로컬 (기본값, GPU 없으면 느림)
TRANSCRIBER_TYPE=openai  # OpenAI Whisper
TRANSCRIBER_TYPE=clova   # Clova Speech (화자구분)
TRANSCRIBER_TYPE=remote  # 외부 Whisper 서버
```

### 4.3 Clova Speech 구현 상세

```python
params = {
    "language": "ko-KR",
    "completion": "sync",
    "diarization": {
        "enable": True,
        "speakerCountMin": 2,
        "speakerCountMax": 2,
    },
}
```

화자 구분 결과는 `SpeakerSegment` 리스트로 파싱:

```json
[
  {"speaker": "화자0", "text": "이 약은 식후 30분에 드세요.", "start": 0.5, "end": 3.2},
  {"speaker": "화자1", "text": "하루에 몇 번 먹나요?", "start": 3.5, "end": 5.1}
]
```

최종 텍스트는 `화자0: ... \n화자1: ...` 형식으로 합산.

### 4.4 STT 예외 처리

| 예외 상황 | 처리 방식 |
|-----------|----------|
| 지원하지 않는 확장자 | 400 Bad Request (mp3·wav·m4a·ogg·flac 만 허용) |
| 파일 크기 150MB 초과 | 413 Request Entity Too Large |
| Clova `result != COMPLETED` | `RuntimeError` 발생 → 500 Internal Server Error |
| 임시 파일 | `try/finally`로 항상 `os.unlink()` 보장 |
| 동기 API 비동기 호출 | `asyncio.to_thread()` 래핑 (이벤트 루프 블로킹 방지) |

---

## 5. 통합 엔드포인트: `POST /input-process`

### 5.1 동작 방식

```
multipart/form-data 요청
├── audio: UploadFile (선택)
├── image: UploadFile (선택)
├── patient_id: str (선택)
├── 환자명: str (선택)
└── 알림매체: "kakao" | "google_calendar" | "sms" | "none"
```

- audio, image **둘 다 없으면** 400 오류
- **둘 다 있으면** `asyncio.gather()`로 **병렬 처리** (OCR + STT 동시 실행)
- 결과를 `AnalyzeRequest` 스키마로 조합하여 반환
- 자동으로 `output/input_process/{YYYYMMDD_HHMMSS}_{환자ID}/` 에 저장

### 5.2 출력 파일 구조

```
output/input_process/
└── 20260522_204615_11/
    ├── stt_raw.txt     # STT 원본 텍스트 (화자 구분 포함)
    ├── ocr_raw.txt     # OCR 구조화 텍스트
    └── response.json   # AnalyzeRequest 전체 JSON
```

### 5.3 실제 출력 예시

**ocr_raw.txt:**
```
처방일자: 2012-11-19
병원명: 미래팜연세약국
약품 1: 오로디핀정 - 1.000 1
약품 2: 코지르탄플러스정 - 1.000 1
약품 3: 아토로우정 10일리그램 - 1.000 1
일반주의사항: ...
```

**stt_raw.txt (Clova 화자구분 시):**
```
화자1: 네 아주 중요함에도 불구하고 ...
화자2: 네 네 교수님의 말씀에 동의하면서도 ...
```

---

## 6. 팀원 API 테스트 가이드

### 6.1 Swagger UI 접속

서버 실행 후:
```
http://localhost:8000/docs
```

### 6.2 테스트 방법

1. **Swagger UI** → `/input-process` 항목 → `Try it out`
2. `image`: 약봉투 사진 파일 첨부
3. `audio`: 음성 파일 첨부 (없으면 생략)
4. `환자명` 입력
5. `알림매체` 선택 (테스트 시 `none` 권장)
6. Execute → 응답 JSON 확인

또는 `curl`:
```bash
curl -X POST http://localhost:8000/input-process \
  -F "image=@/path/to/prescription.jpg" \
  -F "환자명=홍길동" \
  -F "알림매체=none"
```

### 6.3 ENV 설정

`.env.example`을 참고하여 `.env` 작성 (키는 팀장에게 개인 공유):

```env
# OCR
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash   # 기본값, 변경 불필요

# STT 선택
TRANSCRIBER_TYPE=openai         # 화자구분 불필요 시
# TRANSCRIBER_TYPE=clova        # 화자구분 필요 시

# OpenAI Whisper
OPENAI_API_KEY=...

# Clova Speech (화자구분)
CLOVA_INVOKE_URL=...
CLOVA_SECRET_KEY=...
CLOVA_SPEAKER_COUNT_MIN=2
CLOVA_SPEAKER_COUNT_MAX=2
```

**STT 선택 권장:**
- **`openai`** → 화자구분 불필요, 저렴, 빠름 (약봉투만 OCR로 쓸 때)
- **`clova`** → 약사-환자 대화 전체 녹음 시 화자 분리 필요할 때

### 6.4 결과 확인

```
output/input_process/
└── {YYYYMMDD_HHMMSS}_{환자ID}/
    ├── stt_raw.txt
    ├── ocr_raw.txt
    └── response.json   ← 이 JSON이 /analyze 에 넘어가는 형식
```

---

## 7. 개별 엔드포인트 (단위 테스트용)

| 엔드포인트 | 용도 |
|-----------|------|
| `POST /ocr/extract` | 이미지 파일 → OcrResponse JSON |
| `POST /stt/transcribe` | 음성 파일 → TranscribeResponse JSON |
| `POST /input-process` | 이미지 + 음성 → AnalyzeRequest JSON (통합) |

---

## 8. 향후 논의 사항

- `/input-process` 결과를 `POST /analyze`에 자동으로 연결하는 파이프라인  
  (현재는 수동으로 response.json을 /analyze에 붙여넣어야 함)  
  → `docs/api-architecture.md` 참고하여 팀 논의 예정
- 복용량 필드 (`"1.000 1"` 등) 이상 파싱 → 정규식 후처리 추가 검토
- 이미지 품질이 낮을 때 재시도/경고 로직 부재 → confidence score 필요

---

## 9. 파일 구조 요약

```
app/
├── input_process/api/router.py   # 통합 엔드포인트
├── ocr/
│   ├── core/extractor.py         # GeminiExtractor
│   ├── core/config.py            # OCR 환경 설정
│   └── api/schemas.py            # Medicine, OcrResponse
└── stt/
    ├── core/transcriber.py       # 4종 Transcriber 구현
    ├── core/config.py            # STT 환경 설정
    └── api/schemas.py            # TranscribeResponse, SpeakerSegment
```
