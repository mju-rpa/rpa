"""LLM 호출 (mock / ollama / gemini / openai_compatible)."""
import json
import os
import re
from typing import Any

import requests


def mock_initial_analysis(stt: str, ocr: str) -> dict:
    name_match = re.search(r"환자명[:\s]*([^\n]+)", ocr)
    환자명 = name_match.group(1).strip() if name_match else "환자"
    return {
        "환자명": 환자명,
        "진료요약": "STT·OCR 기반 복약 스케줄 초안 (mock)",
        "필수복약리스트": [
            {
                "약품명": "넥시움정",
                "복용시간": "1일 1회 아침 식전 30분",
                "주의사항": "우유와 함께 복용 시 흡수 저하",
            },
            {
                "약품명": "타이레놀정",
                "복용시간": "증상 시 1정",
                "주의사항": "물과 함께 복용",
            },
        ],
        "상호작용_경고": "우유와 식전 복용 시간이 겹칠 수 있음 — 분리 복용 권장",
    }


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def call_llm(system: str, user: str) -> dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return mock_initial_analysis(user, user)

    if provider == "ollama":
        base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        resp = requests.post(
            f"{base}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return _parse_json_object(content)

    if provider == "gemini":
        from google import genai

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        response = client.models.generate_content(
            model=model,
            contents=f"{system}\n\n{user}",
        )
        return _parse_json_object(response.text or "{}")

    if provider == "openai_compatible":
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        resp = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_json_object(content)

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
