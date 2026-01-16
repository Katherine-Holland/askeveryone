# app/ranker.py
import json
import httpx
import re
from app.config import settings

# Used to penalize/avoid stale model disclaimers
_CUTOFF_DISCLAIMER_RE = re.compile(
    r"(as\s+of\s+my\s+last\s+knowledge\s+update|last\s+knowledge\s+update|cannot\s+confirm|can't\s+confirm|i\s+cannot\s+verify|check\s+(a|your)\s+news\s+source)",
    re.IGNORECASE,
)

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

STRICT RULES:
- If intent is LIVE_FRESH: NEVER select an answer that contains "as of my last knowledge update" or similar cutoff disclaimers.
- If intent is LIVE_FRESH: Prefer answers that clearly reflect live results or give verifiable citations.
- If citations were requested: Prefer answers that include sources/links; penalize answers without them.
- If both answers are weak/unsafe/off-topic: choose CLARIFY and ask one short question.

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


def _has_citations(text: str) -> bool:
    if not text:
        return False
    tl = text.lower()
    return ("http://" in tl) or ("https://" in tl) or ("www." in tl) or ("source:" in tl) or ("sources:" in tl) or bool(re.search(r"\[\d+\]", text))


def _looks_like_cutoff_disclaimer(text: str) -> bool:
    if not text:
        return True
    return bool(_CUTOFF_DISCLAIMER_RE.search(text))


def _safe_ranker_fallback(query: str, intent: str, a: str, b: str) -> dict:
    # If ranker fails, do a deterministic best-effort:
    # - For LIVE_FRESH: avoid cutoff disclaimers, prefer citation-bearing
    # - Otherwise: prefer longer non-empty
    a_ok = bool(a and a.strip())
    b_ok = bool(b and b.strip())

    if intent == "LIVE_FRESH":
        a_bad = _looks_like_cutoff_disclaimer(a)
        b_bad = _looks_like_cutoff_disclaimer(b)
        a_cite = _has_citations(a)
        b_cite = _has_citations(b)

        if a_ok and not a_bad and (a_cite or not b_ok):
            pick = "A"
        elif b_ok and not b_bad and (b_cite or not a_ok):
            pick = "B"
        elif a_ok and not a_bad:
            pick = "A"
        elif b_ok and not b_bad:
            pick = "B"
        else:
            pick = "CLARIFY"
    else:
        pick = "A" if len((a or "").strip()) >= len((b or "").strip()) else "B"
        if not a_ok and not b_ok:
            pick = "CLARIFY"

    final = (a if pick == "A" else b) if pick in ("A", "B") else "I couldn’t verify that just now. Want me to try again?"

    return {
        "selection": pick,
        "final_answer": final,
        "scores": {
            "A": {"relevance_to_query": 3, "factual_plausibility": 2, "completeness": 2, "clarity": 3, "safety_compliance": 5, "citation_quality": 2 if _has_citations(a) else 0},
            "B": {"relevance_to_query": 3, "factual_plausibility": 2, "completeness": 2, "clarity": 3, "safety_compliance": 5, "citation_quality": 2 if _has_citations(b) else 0},
        },
        "reason": "Ranker fallback used due to an upstream ranking error.",
        "needs_followup": pick == "CLARIFY",
        "followup_question": "Want me to retry with live sources?" if pick == "CLARIFY" else "",
    }


async def rank_answers(
    query: str,
    intent: str,
    citations_requested: bool,
    provider_a: str,
    answer_a: str,
    provider_b: str,
    answer_b: str,
) -> dict:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    # Guardrail: if LIVE_FRESH and one answer is a cutoff disclaimer, strongly prefer the other
    # (even before calling LLM ranker).
    if intent == "LIVE_FRESH":
        a_bad = _looks_like_cutoff_disclaimer(answer_a)
        b_bad = _looks_like_cutoff_disclaimer(answer_b)
        if a_bad and not b_bad and (answer_b or "").strip():
            return {
                "selection": "B",
                "final_answer": answer_b,
                "scores": {
                    "A": {"relevance_to_query": 3, "factual_plausibility": 0, "completeness": 1, "clarity": 2, "safety_compliance": 5, "citation_quality": 0},
                    "B": {"relevance_to_query": 4, "factual_plausibility": 3, "completeness": 3, "clarity": 4, "safety_compliance": 5, "citation_quality": 3 if _has_citations(answer_b) else 1},
                },
                "reason": "LIVE_FRESH intent: Answer A contained a knowledge cutoff disclaimer; selected B.",
                "needs_followup": False,
                "followup_question": "",
            }
        if b_bad and not a_bad and (answer_a or "").strip():
            return {
                "selection": "A",
                "final_answer": answer_a,
                "scores": {
                    "A": {"relevance_to_query": 4, "factual_plausibility": 3, "completeness": 3, "clarity": 4, "safety_compliance": 5, "citation_quality": 3 if _has_citations(answer_a) else 1},
                    "B": {"relevance_to_query": 3, "factual_plausibility": 0, "completeness": 1, "clarity": 2, "safety_compliance": 5, "citation_quality": 0},
                },
                "reason": "LIVE_FRESH intent: Answer B contained a knowledge cutoff disclaimer; selected A.",
                "needs_followup": False,
                "followup_question": "",
            }

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
            {"role": "system", "content": RANKER_SYSTEM_PROMPT},
            {"role": "user", "content": msg},
        ],
        "temperature": 0.0,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        return _safe_ranker_fallback(query, intent, answer_a, answer_b)
