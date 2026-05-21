import os

# LLM_PROVIDER:
#   mock              — API 없음, 발표/UiPath 연동용 (기본)
#   ollama            — 로컬 Ollama (본인 PC에 있을 때)
#   gemini            — Google AI Studio 무료 API 키
#   openai_compatible — OpenAI / Groq / LM Studio 등 동일 포맷
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

RISK_SCORE_REVIEW_THRESHOLD = int(os.getenv("RISK_SCORE_REVIEW_THRESHOLD", "70"))
MAX_REFLECTION_ROUNDS = int(os.getenv("MAX_REFLECTION_ROUNDS", "2"))


def uses_mock_llm() -> bool:
    return LLM_PROVIDER == "mock"


def llm_provider_label() -> str:
    labels = {
        "mock": "mock (no API)",
        "ollama": f"ollama ({OLLAMA_MODEL})",
        "gemini": f"gemini ({GEMINI_MODEL})",
        "openai_compatible": f"openai_compatible ({OPENAI_MODEL})",
    }
    return labels.get(LLM_PROVIDER, LLM_PROVIDER)
