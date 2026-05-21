import json
import re

import requests

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM response is not valid JSON: {text[:300]}...")


def _full_prompt(system_prompt: str, user_prompt: str) -> str:
    if user_prompt:
        return f"{system_prompt.strip()}\n\n{user_prompt.strip()}"
    return system_prompt.strip()


def _call_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    resp = requests.post(
        f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate",
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def _call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    resp = requests.post(url, json=body, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_openai_compatible(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")
    url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Respond with a single valid JSON object only. No markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_llm(system_prompt: str, user_prompt: str = "") -> dict:
    prompt = _full_prompt(system_prompt, user_prompt)

    if LLM_PROVIDER == "ollama":
        return _extract_json(_call_ollama(prompt))
    if LLM_PROVIDER == "gemini":
        return _extract_json(_call_gemini(prompt))
    if LLM_PROVIDER == "openai_compatible":
        return _extract_json(_call_openai_compatible(prompt))

    raise RuntimeError(
        f"call_llm() requires a live provider, got '{LLM_PROVIDER}'. "
        "Use LLM_PROVIDER=mock for offline demo."
    )


def mock_initial_analysis(stt: str, ocr: str) -> dict:
    """API 없이 돌릴 때 Medical Agent 고정 응답 (Self-Reflection 시연용 초안)."""
    _ = stt, ocr
    return {
        "환자명": "김철수",
        "진료요약": "위산 역류 증상 지속으로 위산 억제제 처방 및 증상에 따른 진통제 처방",
        "필수복약리스트": [
            {
                "약품명": "넥시움정 (위산억제제)",
                "복용시간": "아침 식전 30분",
                "주의사항": "매일 챙겨 드세요.",
            },
            {
                "약품명": "타이레놀정 (진통제)",
                "복용시간": "두통 심할 때만",
                "주의사항": "물과 함께 복용하세요.",
            },
        ],
        "상호작용_경고": "진통제는 우유와 함께 복용하지 마세요.",
    }
