from app.agentic_ai.agent.critic import run_critic_agent
from app.config import MAX_REFLECTION_ROUNDS


def run_self_reflection(
    stt: str, ocr: str, initial: dict, use_mock: bool
) -> tuple[dict, list[dict]]:
    current = initial
    logs: list[dict] = []

    for round_idx in range(1, MAX_REFLECTION_ROUNDS + 1):
        critic = run_critic_agent(stt, ocr, current, use_mock)
        revised = critic.get("revised_analysis")
        logs.append(
            {
                "round": round_idx,
                "critic_feedback": critic.get("feedback", ""),
                "revised": revised is not None,
            }
        )
        if critic.get("approved") or not revised:
            break
        current = revised

    return current, logs
