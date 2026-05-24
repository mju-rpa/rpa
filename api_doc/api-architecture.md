# API 아키텍처 설계 노트

## 1. 현재 구현 구조

### 엔드포인트 목록

| 엔드포인트 | 입력 | 출력 | 역할 |
|-----------|------|------|------|
| `POST /stt/transcribe` | 오디오 파일 (mp3/wav/m4a/ogg/flac) | `TranscribeResponse` | 음성 → 텍스트 변환 |
| `POST /ocr/extract` | 이미지 파일 (jpg/png/webp/heic/heif) | `OcrResponse` | 약봉투 이미지 → 복약정보 추출 |
| `POST /analyze` | `AnalyzeRequest` JSON body | 분석 결과 | Agentic AI 파이프라인 실행 |
| `POST /analyze/file` | JSON 파일 업로드 | 분석 결과 | UiPath용 파일 업로드 방식 |
| `POST /input-process` | 오디오 + 이미지 (multipart, 선택적) | `AnalyzeRequest` JSON | STT + OCR 병렬 → 입력 조립 |

### consult 단계 (`app/consult/`)

진료 상담: STT(음성) + OCR(약봉투). import는 `app.ocr` / `app.stt` (alias → `app.consult.*`).

| 모듈 | 경로 |
|------|------|
| STT | `app/consult/stt/route/`, `schema/`, `core/` |
| OCR | `app/consult/ocr/route/`, `schema/`, `core/` |

### Agentic AI (`app/agentic_ai/`)

- `POST /analyze` → `app/workflow/pipeline.py`
- 서브 모듈: `agent/`, `self_reflection/`, `scoring/`, `hidl/`, `schema/`

### `/input-process` (`app/route/input_process.py`)

- STT + OCR을 `asyncio.gather`로 병렬 실행
- `OcrResponse` → 플랫 문자열 직렬화 → `AnalyzeRequest.ocr_text`로 조립
- `run_pipeline` 호출까지 원스톱 처리
- `audio` / `image` 둘 다 선택적 (하나 이상 필수)

---

## 2. 설계 결정 및 TODO

### 현재 갭: OCR/STT → Agentic AI 연결

현재 STT/OCR 모듈과 분석 파이프라인(`run_pipeline`)은 완전히 분리돼 있다.  
`POST /analyze`는 `stt_text` / `ocr_text`라는 **플랫 문자열**을 직접 받는 구조이므로,  
누군가(UiPath 또는 `/process` 엔드포인트)가 중간에서 결과를 조립해 넘겨야 한다.

워크플로우 다이어그램(`A → D`, `B → D`)은 자동 체이닝처럼 그려져 있지만,  
실제로는 RPA 또는 `/process`가 브릿지 역할을 한다.

### UiPath 연동 방식 비교

**현재 구현 (B안): RPA 3-step 또는 `/process` 단일 호출**

```
[UiPath 방식 1 — 3-step]
POST /stt/transcribe → text 추출
POST /ocr/extract   → medicines 직렬화
POST /analyze       → 분석 결과

[UiPath 방식 2 — 원스톱]
POST /process (audio + image) → 분석 결과
```

B안으로 구현된 이유: 기존 `/stt`, `/ocr`, `/analyze` 엔드포인트를 변경하지 않고  
`/process`만 추가해 최소한의 코드 변경으로 병렬 처리를 도입.

---

### TODO: A안 전환 검토

> **A안 (권장):** 단일 통합 엔드포인트로 전면 재설계

현재 `/process`는 B안 위에 레이어를 얹은 형태라 구조적 중복이 있다.  
아래 이유로 A안 전환을 검토할 것:

**A안이 더 나은 이유:**

1. **UiPath 단순화**: HTTP Request 액티비티 1개로 전체 파이프라인 호출 가능.  
   현재 3-step은 UiPath에서 변수 조립·직렬화 로직을 직접 작성해야 한다.

2. **직렬화 일관성**: 현재 `OcrResponse → ocr_text` 변환이 `/process/api/router.py`의  
   `_ocr_to_text()`에만 존재한다. `/analyze`를 직접 호출하는 경우와 포맷이 달라질 수 있다.

3. **에러 전파 단순화**: 3-step에서는 STT 실패 시 OCR 결과를 버리고 재시도하는 로직이  
   UiPath 쪽에 있어야 한다. 단일 엔드포인트면 서버에서 일관되게 처리 가능.

4. **`/stt`, `/ocr` 단독 엔드포인트 정리 가능**: 단독 호출 필요성이 없어지면  
   엔드포인트 수를 줄여 API 표면을 작게 유지할 수 있다.

**전환 시 작업 범위:**
- `POST /input-process`를 `/analyze` 역할까지 흡수 (또는 `/analyze`를 `/process`로 대체)
- `AnalyzeRequest.stt_text` / `ocr_text` 필드를 내부 전용으로 숨기거나 제거
- `data/sample_input.json` 포맷을 "내부 테스트 전용"으로 명시
