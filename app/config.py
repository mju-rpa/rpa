"""앱 공통 설정 (환경 변수)."""
import os

RISK_SCORE_REVIEW_THRESHOLD = 70
MAX_REFLECTION_ROUNDS = 3

# 위험도 채점에 사용할 약물안전 DB(SQLite, LFS). 없으면 키워드 채점으로 폴백.
DRUG_SAFETY_DB_PATH = os.getenv("DRUG_SAFETY_DB_PATH", "drug_safety.db")


def drug_db_enabled() -> bool:
    return os.getenv("DRUG_DB_ENABLED", "true").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def uses_mock_llm() -> bool:
    return os.getenv("LLM_PROVIDER", "mock").strip().lower() == "mock"


def llm_provider_label() -> str:
    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return "mock (no API)"
    return provider


def get_crewai_llm():
    """CrewAI용 LLM 객체 반환. 환경변수 기반으로 선택."""
    from crewai import LLM

    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()

    if provider == "gemini":
        return LLM(
            model=f"gemini/{os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')}",
            api_key=os.getenv("GEMINI_API_KEY", ""),
        )
    if provider == "openai_compatible":
        return LLM(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    if provider == "ollama":
        return LLM(
            model=f"ollama/{os.getenv('OLLAMA_MODEL', 'llama3.2')}",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    raise ValueError(
        f"LLM_PROVIDER='{provider}' — gemini / openai_compatible / ollama 중 선택"
    )
