import json
import httpx
from app.config import settings

RANKER_SYSTEM_PROMPT = """You are SQL AI Ranker (Ask Everyone). Your job is to choose the best final response for the user, given:
1) the user query
2) two candidate answers from different providers
3) optional context (intent, whether citations were requested)

You MUST output ONLY valid JSON matching the schema below.
Do not include markdown, commentary, or extra keys.

PRIMARY GOALS (in order):
1) Correctness and directness
2) Freshness when required
3) Citations when required
4) Safety
5) Helpfulness

OUTPUT SCHEMA (MUST match exactly):
{
  "selection": "A" | "B" | "MERGE" | "CLARIFY",
  "final_answer": "<string>",
  "scores": {
    "A": {"relevance_to_query": <0-5>, "factual_plausibility": <0-5>, "completeness": <0-5>, "clarity": <0-5>, "safety_compliance": <0-5>, "citation_quality": <0-5>},
    "B": {"relevance_to_query": <0-5>, "factual_plausibility": <0-5>, "completeness": <0-5>, "clarity": <0-5>, "safety_compliance": <0-5>, "citation_quality": <0-5>}
  },
  "reason": "<one short paragraph>",
  "needs_followup": <true_or_false>,
  "followup_question": "<string or empty>"
}

IMPORTANT:
- Return only JSON.
"""

async def rank_answers(query: str, intent: str, citations_requested: bool, provider_a: str, answer_a: str, provider_b: str, answer_b: str) -> dict:
    msg = f"""User query:
<<<
{query}
>>>

Intent: {intent}
User requested citations: {str(citations_requested).lower()}

Candidate Answer A (provider={provider_a}):
<<<
{answer_a}
>>>

Candidate Answer B (provider={provider_b}):
<<<
{answer_b}
>>>
"""
    payload = {
        "model": settings.openai_ranker_model,
        "messages": [
            {"role": "system", "content": RANKER_SYSTEM_PROMpt if False else RANKER_SYSTEM_PROMPT},  # keep lint happy
            {"role": "user", "content": msg},
        ],
        "temperature": 0.0,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=payload,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return json.loads(content)
