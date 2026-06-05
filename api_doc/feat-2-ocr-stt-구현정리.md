# OCR / STT 파이프라인 구현 정리

`feat/edit-score-ocr-stt` 브랜치 기준으로 작성.

---

## 1. 전체 프로세스

### 공통 처리 단계

OCR과 STT 모두 아래 6단계를 동일한 순서로 거친다.

```
① 파일 검증
      확장자·크기 검사. 실패 시 400/413 즉시 반환, 이후 단계 실행 안 함.

② 모델 호출 (1차)
      STT: Transcriber가 오디오를 텍스트로 전사
      OCR: Extractor가 이미지에서 구조화 데이터 추출

③ 점수 산정 (1차)
      LLMValidator → OpenAI 호출로 결과 품질 평가 → (llm_score, llm_reason)
      Scorer → rule_score 계산 후 score = llm_score × 0.5 + rule_score × 0.5

④ 재시도 판단
      score < retry_threshold(0.65) 이면 재시도
      score ≥ 0.65 이면 ⑥으로 바로 이동

⑤ 모델 재호출 + 점수 재산정
      OCR: 재시도 전용 프롬프트(_PROMPT_RETRY)로 재추출
      STT: 동일 파일로 재전사
      재호출 결과로 ③과 동일하게 점수 재산정. retried = true 기록.

⑥ HITL 판정 후 반환
      재시도 여부와 무관하게 최종 score 기준으로 판정.
      score < hitl_threshold(0.50) → status = "hitl_required"
      score ≥ 0.50              → status = "ok"
      파이프라인은 어느 쪽이든 결과를 반환하며 처리를 중단하지 않는다.
      호출자(/input-process)가 hitl 블록을 보고 후속 처리를 결정한다.
```

> **재시도 후에도 점수가 개선되지 않으면** `hitl_required`로 반환된다.
> 재시도가 반드시 `ok`를 보장하지 않는다.

---

### STT 상세 흐름

```
audio 파일
  └─ ① validate_file() — 확장자·150MB 크기 검사
       └─ ② Transcriber.transcribe()   # Whisper / OpenAI / Clova / Remote
            └─ TranscriptionResult (text, duration, segments)
                 └─ ③ SttLLMValidator.validate(text)   ← OpenAI 호출
                       └─ (llm_score, llm_reason)
                            └─ SttScorer.score()  →  ConfidenceResult
                                 └─ ④ score < 0.65?
                                       ├─ Yes → ⑤ 재전사 + 재검증 + 재채점 (retried=true)
                                       └─ No  ┐
                                              └─ ⑥ score < 0.50 → hitl_required
                                                    score ≥ 0.50 → ok
                                                    → SttPipelineResult 반환
```

### OCR — 약봉투 상세 흐름

```
image 파일
  └─ ① validate_file() — 확장자·20MB 크기 검사
       └─ ② Extractor.extract()   # GeminiExtractor | OpenAIExtractor
            └─ OcrResponse (patient_name, medicines[], ...)
                 └─ ③ OcrLLMValidator.validate(response)   ← OpenAI 호출
                       └─ (llm_score, llm_reason)
                            └─ OcrScorer.score()  →  ConfidenceResult
                                 └─ ④ score < 0.65?
                                       ├─ Yes → ⑤ _PROMPT_RETRY로 재추출 + 재검증 + 재채점 (retried=true)
                                       └─ No  ┐
                                              └─ ⑥ score < 0.50 → hitl_required
                                                    score ≥ 0.50 → ok
                                                    → OcrPipelineResult 반환
```

### OCR — 진단서 상세 흐름

```
image 파일
  └─ ① validate_file() — 확장자·20MB 크기 검사
       └─ ② DiagnosisExtractor.extract()   # GeminiDiagnosisExtractor | OpenAIDiagnosisExtractor
            └─ DiagnosisResponse (diagnosis_name, hospital_name, ...)
                 └─ ③ DiagnosisLLMValidator.validate(response)   ← OpenAI 호출
                       └─ (llm_score, llm_reason)
                            └─ DiagnosisScorer.score()  →  ConfidenceResult
                                 └─ ④ score < 0.65?
                                       ├─ Yes → ⑤ 재추출 + 재검증 + 재채점 (retried=true)
                                       └─ No  ┐
                                              └─ ⑥ score < 0.50 → hitl_required
                                                    score ≥ 0.50 → ok
                                                    → DiagnosisPipelineResult 반환
```

### `/input-process` 엔드포인트

STT · OCR(약봉투) · OCR(진단서) 세 파이프라인을 `asyncio.gather`로 병렬 실행한 뒤 결과를 하나의 JSON으로 병합하여 반환한다.

```
POST /input-process
  Form: audio, image, [diagnosis], patient_name, patient_phone

  병렬 실행 ──┬── STT pipeline
              ├── OCR pipeline (약봉투)
              └── OCR pipeline (진단서, 파일 있을 때만)

  응답: patient_name, patient_phone, stt_text, ocr_text, diagnosis_text, hitl{...}
```

---

## 2. Agentic AI 결과 검증 전략

OCR · STT 파이프라인은 아래 네 가지 검증 전략 중 **네 가지 모두**를 적용한다.

### ① Self-check (자가 점검)

1차 추출·전사 결과의 점수가 `retry_threshold(0.65)` 미만이면, LLM에게 **"이전 시도에서 신뢰도가 낮았습니다. 더 주의깊게 읽어주세요"** 라는 힌트(`_PROMPT_RETRY`)를 포함해 동일 입력을 재처리하도록 요청한다. 모델 자신이 이전 결과의 부족함을 인지하고 재시도한다는 점에서 Self-check에 해당한다.

- 적용 대상: `OCRPipeline`, `DiagnosisPipeline`, `STTPipeline`
- 최대 재시도 횟수: 1회 (`retried` 플래그로 기록)

### ② Rule-based check (규칙 기반 검사)

LLM 결과와 독립적으로, 추출·전사 결과가 형식·내용 규칙을 충족하는지 채점한다.

| 대상 | 규칙 |
|------|------|
| OCR 약봉투 | 약품 1개 이상 존재 / DB 약품명 매칭 |
| OCR 진단서 | 진단명 존재 / 병원·의사명 존재 / 환자명 존재 |
| STT | 텍스트 20자 초과 / 의료 키워드 포함 / 텍스트 밀도 정상 |

규칙 통과 여부는 `rule_score`에 반영되며, 실패한 조건은 `response` 필드에 기록된다.

### ③ LLM-as-a-Judge (LLM 평가자)

추출·전사 후 **별도 OpenAI 호출**로 결과 품질을 독립 평가한다. 추출 모델 자신이 부여한 confidence를 그대로 쓰지 않고, 외부 평가자 역할의 LLM이 0.0~1.0 점수와 판단 이유를 반환한다.

| Validator | 평가 질문 |
|-----------|-----------|
| `SttLLMValidator` | 이 전사 텍스트가 의사-환자 약 복용 상담인가? |
| `OcrLLMValidator` | 이 추출 결과가 유효한 약봉투 데이터인가? |
| `DiagnosisLLMValidator` | 이 추출 결과가 유효한 진단서 데이터인가? |

판단 이유는 `confidence.response` 마지막에 `LLM: ...` 형태로 노출된다.

### ④ External verification (외부 데이터 검증)

OCR이 추출한 약품명을 `drug_safety.db`의 `drugs` 테이블(`item_name LIKE '%name%'`)과 대조한다. 실제 존재하는 약품명인지 공식 DB로 확인하는 방식으로, 모델 환각(hallucination)으로 생성된 가짜 약품명을 탐지한다.

- DB 미가용 시 자동 패스(점수 그대로 유지) — CI·LFS 미pull 환경 대응
- 미매칭 시 `response`에 `"DB 약품명 미확인: [약품명]"` 기록

---

## 3. 검증 실패 및 예외 처리

### 검증 결과가 기준 미달인 경우 (score 낮음)

| 상황 | 대응 |
|------|------|
| `score < retry_threshold(0.65)` | Self-check: 모델 재호출 1회. OCR은 `_PROMPT_RETRY` 사용. |
| 재시도 후에도 `score < hitl_threshold(0.50)` | `status = "hitl_required"` 로 반환. 파이프라인은 중단하지 않음. |
| `status = "hitl_required"` 수신 | 호출자(`/input-process`)가 `hitl` 블록에 포함하여 응답. 사람이 직접 검토하도록 위임. |

파이프라인은 어떤 경우에도 결과를 반환하며 실행을 중단하지 않는다. HITL 처리 여부는 최상위 호출자가 결정한다.

### LLM 검증 호출 실패

Validator의 OpenAI 호출이 실패(API 오류, 파싱 실패 등)하면 예외를 catch하여 `(0.5, "LLM 검증 실패")`를 반환한다. 점수가 중간값으로 고정되므로 rule_score가 낮을 경우 자연스럽게 재시도 또는 HITL로 유도된다.

### OCR Extractor / STT Transcriber 초기화 실패

API 키 누락 등으로 파이프라인 생성이 실패하면 503을 반환한다. 이후 단계는 실행되지 않는다.

### drug_safety.db 미가용

`_get_db()`가 `None`을 반환하면 DB 검증 조건을 자동 패스(+0.5)한다. DB 없이도 나머지 파이프라인은 정상 동작한다.

### STT duration=0

`text_density` 계산 시 `duration == 0`이면 ZeroDivisionError 대신 해당 배점 0점 처리 후 `response`에 `"음성 길이 정보 없음"` 기록.

### 파일 검증 실패

| 조건 | HTTP 상태 | 동작 |
|------|-----------|------|
| 지원하지 않는 확장자 | 400 | 즉시 반환, 모델 호출 없음 |
| 파일 크기 초과 (OCR 20MB / STT 150MB) | 413 | 즉시 반환, 모델 호출 없음 |

---

## 4. 신뢰도 점수 산정

### 계산식

```
score = llm_score × 0.5 + rule_score × 0.5
```

### llm_score — LLM 검증 호출

추출·전사 결과를 별도 OpenAI 호출로 평가하여 0.0~1.0 점수와 이유를 반환한다.

| 모듈 | Validator | 판단 질문 |
|------|-----------|-----------|
| STT | `SttLLMValidator` | 이 전사 텍스트가 의사-환자 약 복용 상담인가? |
| OCR 약봉투 | `OcrLLMValidator` | 이 추출 결과가 유효한 약봉투 데이터인가? |
| OCR 진단서 | `DiagnosisLLMValidator` | 이 추출 결과가 유효한 진단서 데이터인가? |

LLM 응답 스키마: `{"score": 0.0~1.0, "reason": "판단 근거 한 문장"}`

### rule_score — 규칙 기반 채점

**OCR 약봉투 (`OcrScorer`)**

| 조건 | 배점 |
|------|------|
| `medicines` 1개 이상 존재 | +0.5 (실패 시 즉시 종료) |
| 약품명 중 하나라도 `drug_safety.db` `drugs.item_name LIKE '%name%'` 매칭 | +0.5 |

**OCR 진단서 (`DiagnosisScorer`)**

| 조건 | 배점 |
|------|------|
| `diagnosis_name` 존재 | +0.5 |
| `hospital_name` 또는 `doctor_name` 존재 | +0.3 |
| `patient_name` 존재 | +0.2 |

**STT (`SttScorer`)**

| 조건 | 배점 |
|------|------|
| 전사 텍스트 20자 초과 | +0.4 |
| 의료 키워드 1개 이상 포함 | +0.4 |
| 텍스트 밀도 2.0 ≤ (글자수 / duration) ≤ 30.0 | +0.2 |

의료 키워드: `처방, 복용, 캡슐, 식후, 식전, 취침전, 타이레놀, 항생제, 소화제, 진통제, 아목시실린, 부작용, 복약, 1일, 1정, 2정, 2회, 3회, mg, 주의사항`

### 임계값

| 임계값 | 기본값 | 환경변수 | 의미 |
|--------|--------|----------|------|
| `retry_threshold` | 0.65 | `OCR_RETRY_THRESHOLD` / `STT_RETRY_THRESHOLD` | 이 값 미만이면 재시도 1회 |
| `hitl_threshold` | 0.50 | `OCR_HITL_THRESHOLD` / `STT_HITL_THRESHOLD` | 재시도 후에도 이 값 미만이면 HITL |

### 응답 confidence 구조

```json
"confidence": {
  "llm_score": 0.1,
  "rule_score": 0.6,
  "score": 0.35,
  "response": "텍스트 길이 정상 | 의료 키워드 없음 | 텍스트 밀도 정상 | LLM: 보건교육 토론으로 의료 상담과 무관함"
}
```

`response` 필드는 rule 판단 결과를 `|` 로 이어 붙인 뒤 LLM 이유를 마지막에 추가한다.

### status 판정

| `score` 범위 | `status` |
|---|---|
| ≥ 0.50 | `ok` |
| < 0.50 | `hitl_required` |

`hitl_required` 시 파이프라인은 처리를 중단하지 않고 WARN 로그를 남긴 뒤 결과를 그대로 반환한다. 처리 중단·재검토 판단은 호출자(`/input-process`)에 위임한다.

---

## 3. 안정성·정확성을 위한 로직

### OCR 공통

| 항목 | 내용 |
|------|------|
| **Markdown 펜스 제거** | LLM이 응답을 ` ```json ... ``` ` 으로 감싸는 경우 `_parse_raw`에서 자동 strip |
| **필드 타입 강제 변환** | `Medicine.coerce_to_str` — dosage 등 숫자로 반환되는 필드를 str로 강제 변환 |
| **재시도 프롬프트** | `_PROMPT_RETRY`에 "불확실해도 최선의 추측값 + 낮은 confidence" 지시 → 빈 응답 방지 |
| **한글 약품명 지시** | 프롬프트에 "이미지에 인쇄된 한글 약품명을 그대로 옮겨 적으세요. 생략하거나 임의로 변경하지 마세요" 명시 |
| **DB 약품 검증** | `drug_safety.db` `drugs` 테이블 LIKE 검색으로 추출된 약품명의 실존 여부를 rule_score에 반영 |

### OCR 제공자 전환 (Gemini ↔ OpenAI)

`OCR_EXTRACTOR_TYPE` 환경변수로 전환. 기본값 `gemini`.

| 값 | Extractor |
|----|-----------|
| `gemini` | `GeminiExtractor` / `GeminiDiagnosisExtractor` |
| `openai` | `OpenAIExtractor` / `OpenAIDiagnosisExtractor` |

OpenAI Extractor는 이미지를 base64로 인코딩해 vision API(`chat.completions`)로 전송한다.

### STT

| 항목 | 내용 |
|------|------|
| **의료 어휘 initial_prompt** | `WhisperTranscriber`가 `initial_prompt`로 의료 용어 목록 주입 — 약품명·복용 지시어 인식률 향상 |
| **화자 분리(Diarization)** | `ClovaSpeechTranscriber`에서 2인 기준 화자 분리 활성화 — 의사/환자 발화 구분 |
| **다중 Transcriber 지원** | `TRANSCRIBER_TYPE` 환경변수로 `local` / `openai` / `clova` / `remote` 전환 |

### 공통

| 항목 | 내용 |
|------|------|
| **LLM 검증 분리** | 추출·전사 후 별도 OpenAI 호출로 결과 품질을 독립적으로 평가 — 자기 보고 confidence의 과신 방지 |
| **PipelineResult 전달** | 서비스 레이어가 텍스트만 반환하던 구조에서 `PipelineResult` 전체 반환 — confidence·status·retried 보존 |
| **병렬 처리** | `/input-process`에서 STT·OCR·진단서를 `asyncio.gather`로 동시 실행 |
| **LLM 원본 응답 로깅** | 모든 LLM 호출(추출·검증)의 원본 JSON을 INFO 레벨로 출력 |

---

## 5. 모듈 구조

```
app/consult/
  stt/
    agents/
      validator.py      # SttLLMValidator
    core/
      pipeline.py       # STTPipeline
      scorer.py         # SttScorer
      transcriber.py    # Whisper / OpenAI / Clova / Remote
      config.py         # STTConfig
    service.py

  ocr/
    agents/
      validator.py      # OcrLLMValidator, DiagnosisLLMValidator
    core/
      pipeline.py       # OCRPipeline, DiagnosisPipeline
      scorer.py         # OcrScorer (DB 연동), DiagnosisScorer
      extractor.py      # Gemini / OpenAI extractor 4종
      config.py         # OCRConfig
    service.py

app/route/
  input_process.py      # POST /input-process — 병렬 실행 · 응답 조립
```
