# OCR / STT 파이프라인 리팩토링 개요

`feat/refact-ocr-stt` 브랜치에서 추가·변경된 로직을 기준으로 작성.

---

## 1. 신뢰도 점수 판정 방식

OCR과 STT 모두 **LLM 점수 50% + 규칙 점수 50%** 로 최종 신뢰도를 산출한다.

```
final = llm_score × 0.5 + rule_score × 0.5
```

### OCR (`OcrScorer`)

규칙 점수는 추출된 `OcrResponse` 필드를 순서대로 검사하여 누적한다.

| 조건 | 배점 | 실패 시 `low_fields` |
|------|------|----------------------|
| `medicines` 1개 이상 | +0.4 | `medicines` → 이후 채점 중단 |
| 약품 중 `dosage` + `frequency` 모두 있는 항목 존재 | +0.3 | `dosage_frequency` |
| `hospital_name` 또는 `prescribed_date` 존재 | +0.2 | `hospital_or_date` |
| `medicines` 수가 1~10개 | +0.1 | `medicines_count` |

LLM 점수는 Gemini 응답 JSON에 포함된 각 필드의 `*_confidence` 값 전체 평균이다.
약품 필드(`name_confidence`, `dosage_confidence` 등)도 포함한다.

### STT (`SttScorer`)

규칙 점수는 `TranscriptionResult`(텍스트·길이·duration)를 검사한다.

| 조건 | 배점 | 실패 시 `low_fields` |
|------|------|----------------------|
| 전사 텍스트 20자 초과 | +0.4 | `text_length` |
| 의료 키워드 1개 이상 포함 | +0.4 | `medical_keywords` |
| 텍스트 밀도 2.0 ≤ (글자수 / duration) ≤ 30.0 | +0.2 | `text_density` |

STT는 현재 LLM 점수를 고정값 `0.5`로 사용한다(Whisper·Clova 모두 self-confidence를 제공하지 않음).

의료 키워드 목록: `처방, 복용, 캡슐, 식후, 식전, 취침전, 타이레놀, 항생제, 소화제, 진통제, 아목시실린, 부작용, 복약, 1일, 1정, 2정, 2회, 3회, mg, 주의사항`

---

## 2. 임계값과 응답

### 임계값

| 임계값 | 기본값 | 의미 |
|--------|--------|------|
| `retry_threshold` | **0.65** | 이 값 미만이면 재시도 1회 |
| `hitl_threshold` | **0.50** | 재시도 후에도 이 값 미만이면 HITL 요청 |

두 임계값은 `OCRPipeline` / `STTPipeline` 생성자 파라미터로 주입 가능하다.

### 재시도 조건

`final < 0.65` 이면 동일 입력으로 한 번 더 처리한다.

- **OCR**: `_PROMPT_RETRY`를 사용해 "이전 시도에서 신뢰도가 낮았습니다. 더 주의깊게 읽어주세요"라는 지시를 추가하여 Gemini를 재호출한다.
- **STT**: 동일 파일 경로로 전사를 다시 실행한다(프롬프트 변경 없음).

재시도 여부는 `retried: bool` 플래그로 결과에 기록된다.

### 응답 status

| `final` 범위 | `status` | 의미 |
|---|---|---|
| ≥ 0.50 | `ok` | 정상 처리 완료 |
| < 0.50 | `hitl_required` | 사람 검토 필요 |

`hitl_required`가 되면 파이프라인은 WARN 레벨 로그를 남기고 결과를 그대로 반환한다 (처리를 중단하지 않음). 상위 레이어(`/input-process`)에서 `hitl` 블록으로 노출하여 호출자가 판단하도록 위임한다.

### `/input-process` 응답의 `hitl` 블록

```json
{
  "hitl": {
    "stt": {
      "status": "hitl_required",
      "retried": true,
      "confidence": {
        "llm_score": 0.5,
        "rule_score": 0.4,
        "final": 0.45,
        "low_fields": ["medical_keywords"]
      }
    },
    "ocr": {
      "status": "ok",
      "retried": false,
      "confidence": { ... }
    }
  }
}
```

요청에 포함된 채널(audio / image)만 블록에 포함된다.

---

## 3. 안정성·정확성을 위한 추가 로직

### OCR

| 항목 | 내용 |
|------|------|
| **Markdown 펜스 제거** | Gemini가 응답을 ` ```json ... ``` ` 으로 감싸는 경우를 `_parse_raw`에서 자동 처리 |
| **필드 타입 강제 변환** | `Medicine.coerce_to_str` validator — dosage 등 숫자로 반환되는 필드를 str로 강제 변환 |
| **LLM 점수 폴백** | confidence 값이 전혀 없으면 llm_score = 0.5로 fallback |
| **재시도 프롬프트** | `_PROMPT_RETRY`에 "불확실해도 최선의 추측값 + 낮은 confidence"를 지시하여 빈 응답 방지 |

### STT

| 항목 | 내용 |
|------|------|
| **의료 어휘 initial_prompt** | WhisperTranscriber가 `initial_prompt`로 의료 용어 목록을 주입 — 약품명·복용 지시어의 인식률 향상 |
| **화자 분리(Diarization)** | ClovaSpeechTranscriber에서 2인 기준 화자 분리 활성화 — 의사/환자 발화 구분 |
| **다중 Transcriber 지원** | WhisperTranscriber(로컬·CPU), OpenAIWhisperTranscriber, ClovaSpeechTranscriber, RemoteWhisperTranscriber — 환경에 따라 교체 가능한 전략 패턴 |
| **duration=0 방어** | `text_density` 계산 시 duration이 0이면 즉시 `low_fields`에 추가하여 ZeroDivisionError 방지 |

### 공통

| 항목 | 내용 |
|------|------|
| **파이프라인 결과 직접 전달** | 서비스 레이어가 텍스트만 반환하던 구조에서 `PipelineResult` 전체를 반환하도록 변경 — confidence·status·retried를 상위 레이어까지 보존 |
| **`to_text` 분리** | 텍스트 추출 로직을 `to_text(data)` 함수로 분리 — 파이프라인 결과를 받아 처리하는 쪽(`/input-process`)과 텍스트만 필요한 레거시 호출처(`transcribe_upload`) 모두 재사용 |
| **병렬 처리** | `/input-process`에서 STT·OCR을 `asyncio.gather`로 동시 실행 |
