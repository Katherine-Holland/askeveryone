# app/router.py
# We are using ChatGPT as the 'telephone exchange' router helper.
# IMPORTANT: For time-sensitive "who is the current X" queries, we do deterministic routing
# to LIVE_FRESH to prevent model cutoff answers reaching users.

import json
import re
from typing import Dict, Any
import httpx
from app.config import settings


ROUTER_SYSTEM_PROMPT = """You are SQL AI Router (Ask Everyone). Your only job is to select the best LLM provider(s) to answer the user’s query.

You MUST output ONLY valid JSON matching the schema below. Do not include any explanation, markdown, commentary, or extra keys.

AVAILABLE PROVIDERS:
- OPENAI
- PERPLEXITY
- GROK
- CLAUDE
- GEMINI

INTENTS (choose exactly one):
- LIVE_FRESH
- WEB_RESEARCH_CITATIONS
- LOCAL_NEAR_ME
- HOW_TO_TROUBLESHOOT
- CODING_TECH
- DATA_MATH_QUANT
- WRITING_EDITING_MARKETING
- CREATIVE_BRAINSTORM
- RECOMMENDATION_NONLOCAL
- SENSITIVE_GUARDED
- GENERAL_CHAT

ROUTING RULES (provider order by intent):
1) LIVE_FRESH: PERPLEXITY > GROK > GEMINI > OPENAI
2) WEB_RESEARCH_CITATIONS: PERPLEXITY > GEMINI > OPENAI > CLAUDE
3) LOCAL_NEAR_ME: PERPLEXITY > GEMINI > OPENAI
4) HOW_TO_TROUBLESHOOT: OPENAI > CLAUDE > GEMINI > PERPLEXITY
5) CODING_TECH: CLAUDE > OPENAI
6) DATA_MATH_QUANT: OPENAI > CLAUDE
7) WRITING_EDITING_MARKETING: CLAUDE > OPENAI
8) CREATIVE_BRAINSTORM: OPENAI > CLAUDE
9) RECOMMENDATION_NONLOCAL: OPENAI > CLAUDE > PERPLEXITY > GEMINI
10) SENSITIVE_GUARDED: CLAUDE > OPENAI > PERPLEXITY (citations only)
11) GENERAL_CHAT: OPENAI > CLAUDE

MULTI-CALL POLICY:
Set multi_call=true when ANY is true:
- confidence < 0.65
- intent is LIVE_FRESH or WEB_RESEARCH_CITATIONS
- user asks to compare ("compare", "versus", "which is best") OR has constraints (budget/time/location) in recommendations

If multi_call=true:
- Choose provider_primary as the first in the intent’s order.
- Choose provider_secondary as the second in the intent’s order.

OUTPUT SCHEMA (MUST match exactly):
{
  "intent": "<ONE_INTENT>",
  "provider_primary": "<ONE_PROVIDER>",
  "provider_secondary": "<ONE_PROVIDER_OR_NULL>",
  "provider_fallbacks": ["<PROVIDER>", "..."],
  "confidence": <NUMBER_0_TO_1>,
  "multi_call": <true_or_false>,
  "reason_codes": ["<REASON_CODE>", "..."]
}

REASON CODES (choose 1-4 max):
- FRESHNESS_TERMS
- NEEDS_CITATIONS
- LOCAL_INTENT
- HOW_TO
- CODE_PRESENT
- MATH_QUANT
- WRITING_EDITING
- CREATIVE
- RECOMMENDATION
- SENSITIVE_DOMAIN
- AMBIGUOUS

IMPORTANT:
- provider_fallbacks must be ordered from best to worst remaining choices for the selected intent.
- If multi_call=false then provider_secondary MUST be null.
- If multi_call=true then provider_secondary MUST NOT be null.
- confidence must be a decimal (e.g., 0.72).
- Return only JSON.
"""

# ----------------------------
# Deterministic freshness gate
# ----------------------------
_FRESHNESS_PATTERNS = [
    # Office holder / role lookups
    r"\bwho\s+is\s+the\s+(current\s+)?(president|prime\s+minister|pm|ceo|chancellor|governor|mayor|king|queen|leader)\b",
    r"\bwho\s+is\s+(the\s+)?(president|prime\s+minister|pm|ceo|chancellor|governor|mayor)\s+of\b",
    r"\bcurrent\s+(president|prime\s+minister|pm|ceo|chancellor|governor|mayor)\b",
    # Freshness phrases
    r"\b(as\s+of\s+today|today|right\s+now|currently|latest|most\s+recent|this\s+week|this\s+month|202[4-9]|203\d)\b",
    # Elections / office changes
    r"\b(election\s+results?|won\s+the\s+election|in\s+office|took\s+office|resigned|appointed)\b",
]
_FRESHNESS_RE = re.compile("|".join(_FRESHNESS_PATTERNS), re.IGNORECASE)

_ALLOWED_INTENTS = {
    "LIVE_FRESH",
    "WEB_RESEARCH_CITATIONS",
    "LOCAL_NEAR_ME",
    "HOW_TO_TROUBLESHOOT",
    "CODING_TECH",
    "DATA_MATH_QUANT",
    "WRITING_EDITING_MARKETING",
    "CREATIVE_BRAINSTORM",
    "RECOMMENDATION_NONLOCAL",
    "SENSITIVE_GUARDED",
    "GENERAL_CHAT",
}
_ALLOWED_PROVIDERS = {"OPENAI", "PERPLEXITY", "GROK", "CLAUDE", "GEMINI"}


def _freshness_required(query: str, features: Dict[str, Any] | None = None) -> bool:
    if _FRESHNESS_RE.search(query or ""):
        return True
    if features and features.get("freshness_required") is True:
        return True
    # If your pre_router sets these, honor them too:
    if features and features.get("politics", False):
        return True
    return False


def _force_live_fresh_route(reason_code: str = "FRESHNESS_TERMS") -> Dict[str, Any]:
    # Keep OpenAI last for LIVE_FRESH so you avoid “I can’t browse” UX.
    return {
        "intent": "LIVE_FRESH",
        "provider_primary": "PERPLEXITY",
        "provider_secondary": "GROK",
        "provider_fallbacks": ["GEMINI", "OPENAI"],
        "confidence": 0.99,
        "multi_call": True,
        "reason_codes": [reason_code],
    }


def _safe_default_route(reason_code: str = "AMBIGUOUS") -> Dict[str, Any]:
    return {
        "intent": "GENERAL_CHAT",
        "provider_primary": "OPENAI",
        "provider_secondary": None,
        "provider_fallbacks": ["CLAUDE"],
        "confidence": 0.55,
        "multi_call": False,
        "reason_codes": [reason_code],
    }


def _validate_and_normalize_route(route: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures route is usable even if the router model returns something slightly off.
    """
    if not isinstance(route, dict):
        return _safe_default_route("AMBIGUOUS")

    intent = route.get("intent")
    if intent not in _ALLOWED_INTENTS:
        return _safe_default_route("AMBIGUOUS")

    provider_primary = route.get("provider_primary")
    if provider_primary not in _ALLOWED_PROVIDERS:
        return _safe_default_route("AMBIGUOUS")

    provider_secondary = route.get("provider_secondary")
    if provider_secondary is not None and provider_secondary not in _ALLOWED_PROVIDERS:
        provider_secondary = None

    fallbacks = route.get("provider_fallbacks") or []
    if not isinstance(fallbacks, list):
        fallbacks = []
    fallbacks = [p for p in fallbacks if p in _ALLOWED_PROVIDERS and p != provider_primary]
    if provider_secondary:
        fallbacks = [p for p in fallbacks if p != provider_secondary]

    # confidence
    try:
        conf = float(route.get("confidence", 0.5))
    except Exception:
        conf = 0.5
    conf = max(0.0, min(conf, 1.0))

    multi_call = bool(route.get("multi_call", False))

    # enforce schema rule: provider_secondary nullability
    if not multi_call:
        provider_secondary = None
    else:
        if provider_secondary is None:
            # try to pick first fallback as secondary
            provider_secondary = fallbacks[0] if fallbacks else "GROK"
            if provider_secondary == provider_primary:
                provider_secondary = "GROK" if provider_primary != "GROK" else "GEMINI"

    reason_codes = route.get("reason_codes") or []
    if not isinstance(reason_codes, list):
        reason_codes = ["AMBIGUOUS"]
    reason_codes = [str(x) for x in reason_codes][:4] or ["AMBIGUOUS"]

    return {
        "intent": intent,
        "provider_primary": provider_primary,
        "provider_secondary": provider_secondary,
        "provider_fallbacks": fallbacks,
        "confidence": conf,
        "multi_call": multi_call,
        "reason_codes": reason_codes,
    }


async def route_query(query: str, features: dict) -> dict:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    # --- HARD OVERRIDE: time-sensitive queries must route to LIVE_FRESH ---
    if _freshness_required(query, features):
        return _force_live_fresh_route("FRESHNESS_TERMS")

    user_msg = f"""User query:
<<<
{query}
>>>

Feature hints (from heuristic):
{json.dumps(features, ensure_ascii=False)}
"""

    payload = {
        "model": settings.openai_router_model,
        "messages": [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
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

        # Router model must return JSON. If not, fail closed to safe default.
        route_raw = json.loads(content)
        route = _validate_and_normalize_route(route_raw)

    except Exception:
        route = _safe_default_route("AMBIGUOUS")

    # --- POST-VALIDATION: never allow freshness-required queries to slip ---
    if _freshness_required(query, features) and route.get("intent") != "LIVE_FRESH":
        return _force_live_fresh_route("FRESHNESS_TERMS")

    return route
