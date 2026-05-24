"""앱 공통 설정 (환경 변수)."""
import os

RISK_SCORE_REVIEW_THRESHOLD = 70
MAX_REFLECTION_ROUNDS = 3


def uses_mock_llm() -> bool:
    return os.getenv("LLM_PROVIDER", "mock").strip().lower() == "mock"


def llm_provider_label() -> str:
    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return "mock (no API)"
    return provider
