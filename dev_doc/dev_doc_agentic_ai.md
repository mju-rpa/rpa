# Agentic AI 모듈 개발 문서

> **위치:** `app/agentic_ai/`  
> **담당 단계:** step02 — STT·OCR 결과 수신 → CrewAI 분석 → 결과 반환

---

## 1. 디렉터리 구조

```
app/agentic_ai/
├── agent/
│   ├── medical.py             # Medical Agent (복약 초안 생성)
│   ├── critic.py              # Critic Agent (Self-Reflection)
│   └── crewai_agents.py       # CrewAI 5개 Agent 파이프라인 (핵심)
├── db/
│   ├── drug_safety.db         # 관계형 DB (약품 정보, 병용금기, 용량/기간주의)
│   ├── chroma_db/             # 벡터 DB (ChromaDB)
│   ├── db_query.py            # DB 조회 인터페이스
│   ├── build_relational_db.py # 관계형 DB 구축 스크립트
│   └── build_vector_db.py     # 벡터 DB 구축 스크립트
├── self_reflection/
│   └── loop.py                # Critic 반복 실행 루프
├── scoring/
│   └── risk.py                # 위험도 점수 (mock 모드용)
├── hidl/
│   └── gate.py                # Human-In-The-Loop 게이트
└── schema/
    └── models.py              # Pydantic 데이터 모델
```

---

## 2. 실행 흐름

```
step02.agentic_analyze_reflect_score(stt, ocr, 환자명, 알림매체)
  │
  ├─ 1. medical.py           → analysis 초안 생성
  ├─ 2. self_reflection/loop → Critic Agent 검증 (최대 N라운드)
  │
  ├─ [mock 모드]  → mock 결과 반환
  │
  └─ [실제 LLM]  → crewai_agents.run_crewai_pipeline()
       ├─ InputValidator     → STT·OCR 검증, 약품명 DB 매칭
       ├─ MedicationAnalyzer → 복약 정보 분석, 불일치 감지
       ├─ RiskEvaluator      → DB 기반 주의사항 분류
       ├─ GuidanceWriter     → 환자 맞춤 안내문 생성
       └─ ActionPlanner      → RPA 액션 결정
```

---

## 3. CrewAI Agent 5개 구성

> 수업 실습(chapter6) `Process.sequential` + `context` 연결 구조 동일 적용

| Agent | 수업 실습 대응 | 역할 | DB 사용 |
|-------|-------------|------|--------|
| InputValidator | (신규) | STT·OCR 품질 검증, 약품명 DB 교정 | 관계형 DB |
| MedicationAnalyzer | Research Agent | 복약 분석, 불일치 감지 | 벡터 DB |
| RiskEvaluator | Fact Check Agent | 주의사항 심각/주의/참고 분류 | 관계형 + 벡터 DB |
| GuidanceWriter | Review Agent | 환자 맞춤 안내문 생성 | 원본 텍스트 (방법 3) |
| ActionPlanner | Report Agent | 알림 계획, RPA 액션 결정 | - |

---

## 4. DB 구성

### 관계형 DB (drug_safety.db) — 정확 매칭용

| 테이블 | 출처 | 용도 |
|--------|------|------|
| drugs | 식약처 e약은요 | 약품명 → 효능/복용법/주의사항/상호작용 |
| drug_interactions | 한국의약품안전관리원 병용금기 | 두 약품 병용금기 여부 확인 |
| dose_limits | 한국의약품안전관리원 용량주의 | 1일 최대 투여량 초과 여부 |
| duration_limits | 한국의약품안전관리원 투여기간주의 | 최대 투여기간 초과 여부 |

### 벡터 DB (ChromaDB / chroma_db/) — 의미 검색용

| 컬렉션 | 내용 | 검색 예시 |
|--------|------|---------|
| drug_warnings | intrc + atpn + se 자연어 | "우유랑 먹으면 안 되는 약" |
| elderly_warnings | 노인주의 약품상세정보 | "낙상 위험 약" |
| interaction_reasons | 병용금기 금기사유 | "세로토닌 증후군 유발" |

---

## 5. RAG 할루시네이션 방지 전략

### 방법 1. 메타데이터 필터링
벡터 검색 전에 약품명으로 먼저 필터링

```python
col.query(
    query_texts=["주의사항"],
    where={"item_name": "넥시움정"},  # 약품명 필터
    n_results=3,
)
```

### 방법 2. 하이브리드 검색
관계형 DB 정확 매칭 → 실패 시 벡터 검색으로 보완

```python
info = db.get_drug_info("넥시움정")   # 관계형 먼저
if not info:
    db.search_warnings("넥시움정")    # 실패 시 벡터
```

### 방법 3. 원본 텍스트 전달
출처 명시한 원본 텍스트를 LLM에 그대로 전달

```python
context = db.build_rag_context("넥시움정")
# → "[약품: 넥시움정]\n  - 상호작용 (출처: 식약처 e약은요): ..."
# Task description에 삽입 후 "DB에 없는 내용은 추측하지 마라" 지시
```

---

## 6. 주의사항 분류 기준

| 분류 | 기준 | 사용자 안내 |
|------|------|-----------|
| 심각 | "복용하지 마십시오" 포함 | 🚨 약사 문의 강력 권고 |
| 주의 | "의사 또는 약사와 상의하십시오" 포함 | ⚠️ 확인 요청 |
| 참고 | 그 외 일반 주의사항 | 📌 일반 안내 |
| 용량초과 | 1일 최대 투여량 초과 | 🚨 즉시 경고 |
| 기간초과 | 최대 투여기간 초과 | ⚠️ 확인 요청 |
| 노인주의 | 노인 주의 DB 매칭 | ⚠️ 노인 환자 확인 |

---

## 7. step02 반환값

```python
{
    "analysis": {
        "환자명":           str,
        "진료요약":         str,
        "필수복약리스트":    list,
        "상호작용_경고":    str,
        "stt_ocr_불일치":  list,
        "환자맞춤_복약안내": str,
        "핵심_주의사항":    str,
    },
    "reflection_logs": list,
    "warnings": {
        "심각":    list,
        "주의":    list,
        "참고":    list,
        "용량초과": list,
        "기간초과": list,
        "노인주의": list,
        "총_건수":  dict,
    },
    "validation": {
        "ocr_유효":      bool,
        "stt_유효":      bool,
        "약품명_DB매칭":  list,
        "검증_경고":     list,
    },
    "action_plan": {
        "알림_우선순위": str,
        "권장_액션":    list,
    },
    "use_mock": bool,
}
```

---

## 8. 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 선택 | `mock` |
| `GEMINI_API_KEY` | Gemini API 키 | - |
| `GEMINI_MODEL` | Gemini 모델명 | `gemini-2.0-flash` |
| `OPENAI_API_KEY` | OpenAI API 키 | - |
| `OPENAI_MODEL` | OpenAI 모델명 | `gpt-4o-mini` |
| `OPENAI_BASE_URL` | OpenAI 호환 엔드포인트 | `https://api.openai.com/v1` |
| `RISK_SCORE_REVIEW_THRESHOLD` | 재검토 기준점 | `70` |
| `MAX_REFLECTION_ROUNDS` | Self-Reflection 최대 횟수 | `3` |

---

## 9. requirements.txt 추가 항목

```
crewai>=0.80.0
chromadb>=0.6.0
```

---

## 10. DB 구축 방법

```bash
# 1. DB 폴더 생성
mkdir app/agentic_ai/db
cd app/agentic_ai/db

# 2. CSV + medication.db 파일을 db/ 폴더에 복사

# 3. 관계형 DB 구축
python build_relational_db.py
# → drug_safety.db 생성

# 4. 벡터 DB 구축
python build_vector_db.py
# → chroma_db/ 폴더 생성
```
