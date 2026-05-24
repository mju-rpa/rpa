# 6. LLM 연동 — 아무거나 OK (Ollama 필수 아님)

## 기본 원칙

| 목적 | 추천 `LLM_PROVIDER` |
|------|---------------------|
| **발표·UiPath만** | `mock` (설정 없음, 기본값) |
| **본인 PC Ollama** | `ollama` |
| **클라우드·키만 있으면 됨** | `gemini` (무료 키 발급 쉬움) |
| **Groq / OpenAI / LM Studio** | `openai_compatible` |

**Ollama는 선택 사항입니다.** 예전 가이드에 Ollama가 많이 나온 이유는 팀장 PC에 이미 설치돼 있었기 때문이고, 과제 데모는 **`mock`만으로도 Self-Reflection·점수·리포트까지 전부 동작**합니다.

---

## 1) mock (기본, 추천)

```powershell
cd demo
pip install -r requirements.txt
python run_standalone.py
```

- Medical Agent: 고정 JSON  
- Critic: 코드로 우유·식전 충돌 → 1회 수정 (Self-Reflection 시연)  
- API 키·Ollama 불필요  

---

## 2) ollama (있을 때만)

```powershell
ollama pull llama3.2
$env:LLM_PROVIDER="ollama"
$env:PYTHONIOENCODING="utf-8"
python run_standalone.py
```

---

## 3) gemini (Ollama 없을 때 실 LLM 예시)

1. https://aistudio.google.com/apikey 에서 키 발급  
2. `demo/.env.example` 를 `.env`로 복사 후:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=발급받은키
```

3. PowerShell:

```powershell
$env:LLM_PROVIDER="gemini"
$env:GEMINI_API_KEY="발급받은키"
python run_standalone.py
```

Medical·Critic 모두 **실제 LLM** 호출 (Self-Reflection도 LLM 응답에 따름).

---

## 4) openai_compatible

OpenAI, **Groq**(무료 티어), LM Studio 로컬 서버 등 Chat Completions 호환 URL.

```powershell
$env:LLM_PROVIDER="openai_compatible"
$env:OPENAI_API_KEY="gsk_..."   # Groq 예
$env:OPENAI_BASE_URL="https://api.groq.com/openai/v1"
$env:OPENAI_MODEL="llama-3.3-70b-versatile"
```

---

## Render 배포

무료 PaaS에는 **mock 권장** (슬립·키 관리 단순).

실 LLM 쓰려면 Render Environment Variables에 `LLM_PROVIDER=gemini`, `GEMINI_API_KEY=...` 설정.

---

## 확인

```powershell
Invoke-RestMethod http://localhost:8000/health
```

응답 예: `"llm_provider": "mock (no API)", "uses_mock": true`
