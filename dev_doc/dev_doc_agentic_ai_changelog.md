# Agentic AI 변경 이력

> **작성자:** 최홍규  
> **최종 수정:** 2026-06-05  
> **브랜치:** feat/agentic-ai-crewai

---

## 변경 배경

기존 구조에서 아래 두 가지 문제가 제기됨

1. **LLM 할루시네이션 위험** — LLM이 약물 효과·위험도를 임의로 판단하는 구조
2. **위험도 점수 근거 불명확** — 임의 감점 기준(상호작용 -30점 등)으로 설명력 부족

---

## 핵심 변경 원칙

```
✅ 모든 판단은 DB 정보만 기반으로 수행
✅ LLM은 텍스트 파싱/요약/비교/정리만 수행
❌ LLM이 약물 효과·위험도를 임의로 판단하는 것 절대 금지
❌ DB에 없는 내용은 절대 추측하지 않음 → "데이터 없음"으로 표시
```

---

## 1. Agent 구조 변경

### 기존 (4개)

| Agent | 역할 |
|-------|------|
| MedicationAnalyzer | STT·OCR 통합 분석 |
| RiskEvaluator | 위험도 0~100점 산정 |
| GuidanceWriter | 환자 맞춤 안내문 생성 |
| ActionPlanner | RPA 액션 결정 |

### 변경 후 (5개)

| Agent | 수업 대응 | 역할 |
|-------|---------|------|
| STT Summarizer | Research Agent | STT 요약, 언급 약품 추출 |
| OCR Medication Data Agent | Research Agent | OCR 추출 + DB 조회 |
| Prescription Reviewer | Fact Check Agent | 불일치 체크 + Self-Reflection |
| Risk Evaluator | Review Agent | DB 건수 기반 군집 분류 + HITL |
| Guidance Writer | Report Agent | 보고서용 JSON 구조화 |

---

## 2. 위험도 판단 방식 변경

### 기존

```python
# 임의 감점 기준
위험도 점수 = 100 - (상호작용 경고 * 30) - (불일치 * 20) - (5회 초과 * 10)
재검토_필요 = 최종점수 < 70
```

### 변경 후

```python
# DB 건수 기반 군집 분류
군집 = "위험"  # 심각 항목 1건 이상 OR 불일치 있음
군집 = "주의"  # 주의 항목 1건 이상
군집 = "일반"  # 이상 없음

HITL_필요 = 군집 in ("위험", "주의")
```

---

## 3. DB 구성 추가

### 관계형 DB (drug_safety.db)

| 테이블 | 출처 | 내용 |
|--------|------|------|
| drugs | 식약처 e약은요 | 약품 기본 정보 (4,737개) |
| drug_interactions | 한국의약품안전관리원 | 병용금기 (542,996건) |
| dose_limits | 한국의약품안전관리원 | 용량주의 (7,041건) |
| duration_limits | 한국의약품안전관리원 | 투여기간주의 (410건) |

### 벡터 DB (ChromaDB / chroma_db/)

| 컬렉션 | 내용 |
|--------|------|
| drug_warnings | intrc + atpn + se 자연어 |
| elderly_warnings | 노인주의 약품상세정보 |
| interaction_reasons | 병용금기 금기사유 |

**임베딩 모델:** `snunlp/KR-SBERT-V40K-klueNLI-augSTS` (한국어 특화)

### RAG 할루시네이션 방지 3가지

- **방법 1:** 메타데이터 필터링 (약품명으로 먼저 필터)
- **방법 2:** 하이브리드 검색 (관계형 먼저, 실패 시 벡터)
- **방법 3:** 원본 텍스트 전달 (출처 명시, "DB에 없는 내용 추측 금지" 지시)

---

## 4. HITL 구조 추가

Risk Evaluator 결과가 위험/주의이면 HITL 플래그 설정

```python
{
    "HITL_필요": True,
    "HITL_메시지": "복약 주의사항 N건이 발견되었습니다. 계속 진행하시겠습니까?"
}
```

UiPath에서 처리:
```
HITL_필요 = true
        ↓
MessageBox → 주의사항 목록 표시
InputDialog → 예/아니오 선택
        ↓
아니오 → 프로세스 종료
예 → 다음 단계 진행
```

---

## 5. 반환값 구조 변경

### 기존

```python
{
    "analysis": {...},
    "risk_score": {"최종점수": 70, "재검토_필요": false},
    "reflection_logs": [...],
    "action_plan": {...}
}
```

### 변경 후

```python
{
    "stt_summary": {
        "증상_요약": str,
        "언급_약품": list,
        "상담_맥락": str,
    },
    "ocr_data": {
        "약품_목록": [{"약품명", "복용시간", "복용횟수", "용량", "DB_정보"}]
    },
    "mismatch": {
        "불일치_목록": list,
        "일치_항목": list,
        "재검토_완료": bool,
    },
    "risk": {
        "군집": str,              # 위험/주의/일반
        "주의사항_건수": int,
        "불일치_건수": int,
        "분류_근거": list,
        "HITL_필요": bool,
        "HITL_메시지": str,
    },
    "guidance": {
        "환자명": str,
        "약품_목록": list,
        "불일치_항목": list,
        "군집": str,
        "주의사항": list,
        "알림_메시지": str,
        "csv_rows": list,
    },
    "use_mock": bool,
}
```

---

## 6. 수정된 파일 목록

### 새로 생성

| 파일 | 경로 |
|------|------|
| `crewai_agents.py` | `app/agentic_ai/agent/crewai_agents.py` |
| `db_query.py` | `app/agentic_ai/db/db_query.py` |
| `test_input_normal.json` | 루트 |
| `test_input_mismatch.json` | 루트 |

### 수정

| 파일 | 경로 | 변경 내용 |
|------|------|---------|
| `step02_agentic_analyze_reflect_score.py` | `app/workflow/` | CrewAI 5-Agent 호출로 변경 |
| `run_pipeline.py` | `app/workflow/` | 알림매체 파라미터 추가, 반환값 구조 변경 |
| `step04_rpa_notify_output.py` | `app/workflow/` | 최종점수 → 군집 기반으로 변경 |
| `response.py` | `app/rpa/uipath/` | final_score 호환 처리, risk_cluster 추가 |
| `config.py` | `app/` | get_crewai_llm() 추가 |
| `requirements.txt` | 루트 | crewai, chromadb 추가 |

---

## 7. 로컬 테스트 결과

```
테스트 일시: 2026-06-05
테스트 모드: LLM_PROVIDER=mock

✅ POST /demo/pipeline?sample=normal → 200 OK
✅ stt_summary 정상 반환
✅ ocr_data + DB 정보 정상 반환
✅ mismatch 불일치 체크 정상
✅ risk 군집=주의, HITL_필요=true 정상
✅ guidance csv_rows 정상 반환
✅ UiPath HTTP Request → 응답 수신 성공
✅ UiPath HITL 팝업 (환자명, 위험등급) 정상 표시
```

---

## 8. 팀원 연동 필요 사항

### 정민규님

```python
# run_pipeline.py 알림매체 파라미터 확인
agentic_analyze_reflect_score(stt, ocr, req.환자명, req.알림매체)

# step04 risk 키 변경 확인
risk["군집"]      # 위험/주의/일반
risk["HITL_필요"]  # bool
```

### 정아영님

```python
# 보고서 생성 시 아래 데이터 사용
guidance["csv_rows"]     # 약품별 데이터
guidance["알림_메시지"]   # 알림 발송용
guidance["군집"]          # 위험등급
```

### DB 파일 공유

```
drug_safety.db  → 구글 드라이브로 공유
chroma_db/      → 구글 드라이브로 공유
```
