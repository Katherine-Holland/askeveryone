# app/orchestrator.py
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import re

from app.pre_router import extract_features, pre_route
from app.router import route_query
from app.ranker import rank_answers

from app.providers.openai_provider import OpenAIProvider
from app.providers.perplexity_provider import PerplexityProvider
from app.providers.grok_provider import GrokProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.huggingface_provider import HuggingFaceProvider
from app.providers.llama_provider import LlamaProvider
from app.providers.base import ProviderError

from app.db.session import get_session
from app.db import repo as dbrepo

from app.limits import cooldown_provider, is_provider_available


PROVIDERS = {
    "OPENAI": OpenAIProvider(),
    "PERPLEXITY": PerplexityProvider(),
    "GROK": GrokProvider(),
    "CLAUDE": ClaudeProvider(),
    "GEMINI": GeminiProvider(),
    "LLAMA": LlamaProvider(),
    "HUGGINGFACE": HuggingFaceProvider(),
}

# ----------------------------
# Cost controls (defaults)
# ----------------------------
PRIMARY_MAX_TOKENS_DEFAULT = 650          # keep cheap by default
SECONDARY_MAX_TOKENS_DEFAULT = 350        # fallback is "safety net"
LIVE_FRESH_PRIMARY_MAX_TOKENS = 900       # allow slightly longer for live queries
WEB_CITE_PRIMARY_MAX_TOKENS = 900         # citations/research benefit from length

# ----------------------------
# Provider refusal / stall detection
# (prevents "I can't browse/live" OR "knowledge cutoff" reaching UI)
# ----------------------------
_REFUSAL_PATTERNS = [
    # classic "can't browse" / "no live data"
    r"\b(i (do not|don't) have access to (real[-\s]?time|live|current) (data|news|information))\b",
    r"\b(i (cannot|can't) (browse|access the internet|check (the )?web|verify in real time))\b",
    r"\b(i (do not|don't) have (the )?ability to browse the web)\b",

    # deflections
    r"\b(check (google news|google trends|twitter|x|a news aggregator|your preferred aggregator))\b",
    r"\b(headlines shift fast)\b",
    r"\b(what('s| is) a specific topic you're curious about\?)\b",

    # NEW: "knowledge cutoff" disclaimers (the edge case you hit)
    r"\b(as of my last knowledge update)\b",
    r"\b(last knowledge update)\b",
    r"\b(i cannot confirm if .{0,40} (still|currently) (in office|true|accurate))\b",
    r"\b(i (cannot|can't) confirm (that|this) (is|it's) still)\b",
]

def _looks_like_refusal(text: str) -> bool:
    if not text:
        return True
    t = text.strip()
    if len(t) < 20:
        return True
    tl = t.lower()
    for pat in _REFUSAL_PATTERNS:
        if re.search(pat, tl, re.IGNORECASE):
            return True
    return False


# ----------------------------
# Deterministic freshness gate (extra safety)
# If query matches office-holder / time-sensitive identity, force LIVE_FRESH behavior.
# ----------------------------
_FRESHNESS_PATTERNS = [
    r"\bwho\s+is\s+the\s+(current\s+)?(president|prime\s+minister|pm|ceo|chancellor|governor|mayor|king|queen|leader)\b",
    r"\bwho\s+is\s+(the\s+)?(president|prime\s+minister|pm|ceo|chancellor|governor|mayor)\s+of\b",
    r"\bcurrent\s+(president|prime\s+minister|pm|ceo|chancellor|governor|mayor)\b",
    r"\b(as\s+of\s+today|today|right\s+now|currently|latest|most\s+recent|this\s+week|this\s+month)\b",
    r"\b(election\s+results?|won\s+the\s+election|in\s+office|took\s+office|resigned|appointed)\b",
]
_FRESHNESS_RE = re.compile("|".join(_FRESHNESS_PATTERNS), re.IGNORECASE)

def _freshness_required(query: str, features: Dict[str, bool]) -> bool:
    if _FRESHNESS_RE.search(query or ""):
        return True
    # also honor your existing pre-router freshness
    if features.get("freshness", False):
        return True
    return False


def _is_rate_limit_error(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "429" in msg
        or "rate limit" in msg
        or "quota" in msg
        or "too many requests" in msg
        or "resource exhausted" in msg
    )

def _safe_db_rollback(db) -> None:
    try:
        if db:
            db.rollback()
    except Exception:
        pass

def _safe_db_commit(db) -> None:
    """
    IMPORTANT: Without committing query rows, billing_repo.count_queries_last_24h()
    will keep returning 0, which makes free users look unlimited.
    """
    try:
        if db:
            db.commit()
    except Exception:
        _safe_db_rollback(db)

def _safe_db_close(db) -> None:
    try:
        if db:
            db.close()
    except Exception:
        pass


def _last_user_topic(conversation: List[Dict[str, str]]) -> str:
    for m in reversed(conversation or []):
        if (m.get("role") == "user") and (m.get("content") or "").strip():
            t = (m["content"] or "").strip()
            t = re.sub(r"\s+", " ", t)
            return t[:180]
    return ""

def _extract_destination_like_phrase(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(?:get to|to)\s+([A-Za-z0-9][A-Za-z0-9\-\s]{1,40})", text, re.IGNORECASE)
    if m:
        dest = m.group(1).strip()
        dest = re.sub(r"\s+", " ", dest)
        return dest[:60]
    if re.search(r"\bmoon\b", text, re.IGNORECASE):
        return "the Moon"
    return ""

def _detect_followup(query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return False
    follow_markers = [
        "how long", "how far", "what about", "what if", "can i", "could i",
        "and then", "get there", "that", "it", "there", "this", "them", "those",
    ]
    return any(p in q for p in follow_markers)

def _derive_conversation_state(
    *,
    query: str,
    intent: str,
    conversation: Optional[List[Dict[str, str]]] = None,
    memory: str = "",
) -> str:
    conversation = conversation or []
    followup = _detect_followup((query or "").strip())
    last_topic_hint = _last_user_topic(conversation)
    mem_hint = (memory or "").strip()

    followup_note = ""
    if followup:
        dest = _extract_destination_like_phrase(last_topic_hint) or _extract_destination_like_phrase(mem_hint)
        if dest:
            followup_note = f"Follow-up detected. Likely referent/destination: {dest}."
        else:
            followup_note = "Follow-up detected. Resolve pronouns like 'there/it/that' using prior turns."

    lines: List[str] = []
    if mem_hint:
        lines.append("Memory summary (stored):")
        lines.append(mem_hint[:800])
    if last_topic_hint:
        lines.append("Recent user context (last user message):")
        lines.append(last_topic_hint)
    if followup_note:
        lines.append("Follow-up resolution:")
        lines.append(followup_note)
    if intent:
        lines.append(f"Router intent: {intent}")

    return "\n".join(lines).strip()

def _build_messages(
    *,
    query: str,
    intent: str,
    conversation: Optional[List[Dict[str, str]]] = None,
    memory: str = "",
    today_utc: str = "",
) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = []

    conv_state = _derive_conversation_state(query=query, intent=intent, conversation=conversation, memory=memory)
    if conv_state:
        msgs.append({"role": "system", "content": f"Conversation State (deterministic):\n{conv_state}"})

    system_lines = [
        "You are Seekle, a helpful assistant.",
        "Use the conversation state and prior turns to answer follow-ups directly.",
        "If the user changes topic, follow the new topic.",
    ]
    if today_utc:
        system_lines.append(f"Today's date (UTC): {today_utc}")

    msgs.append({"role": "system", "content": "\n".join(system_lines)})

    if conversation:
        for m in conversation:
            role = (m.get("role") or "").strip()
            content = (m.get("content") or "").strip()
            if not role or not content:
                continue
            if role not in ("user", "assistant"):
                continue
            msgs.append({"role": role, "content": content})

    msgs.append({"role": "user", "content": (query or "").strip()})
    return msgs


async def call_provider(provider_name: str, query: str, intent: str, meta: Dict[str, Any]) -> str:
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ProviderError(f"Provider not implemented: {provider_name}")
    return await provider.ask(query=query, intent=intent, meta=meta)


async def call_provider_logged(
    db,
    query_uuid,
    provider_name: str,
    query: str,
    intent: str,
    meta: Dict[str, Any],
) -> str:
    pc_id = None
    start = time.perf_counter()

    if db:
        try:
            pc = dbrepo.create_provider_call(db, query_id=query_uuid, provider=provider_name)
            pc_id = pc.call_id
            _safe_db_commit(db)
        except Exception:
            _safe_db_rollback(db)
            db = None

    try:
        answer = await call_provider(provider_name, query, intent, meta)
        latency_ms = int((time.perf_counter() - start) * 1000)

        if db and pc_id:
            try:
                excerpt = (answer[:300] + "…") if len(answer) > 300 else answer
                dbrepo.finish_provider_call(
                    db,
                    call_id=pc_id,
                    success=True,
                    latency_ms=latency_ms,
                    answer_excerpt=excerpt,
                )
                _safe_db_commit(db)
            except Exception:
                _safe_db_rollback(db)

        return answer

    except Exception:
        latency_ms = int((time.perf_counter() - start) * 1000)

        if db and pc_id:
            try:
                dbrepo.finish_provider_call(
                    db,
                    call_id=pc_id,
                    success=False,
                    latency_ms=latency_ms,
                    error_code="PROVIDER_ERROR",
                )
                _safe_db_commit(db)
            except Exception:
                _safe_db_rollback(db)

        raise


# ----------------------------
# Provider selection tweaks (cheap by default)
# ----------------------------
def _force_single_call(intent: str) -> bool:
    # Keep most intents single-call by default.
    return intent in {
        "GENERAL_CHAT",
        "CREATIVE_BRAINSTORM",
        "WRITING_EDITING_MARKETING",
        "RECOMMENDATION_NONLOCAL",
        "DATA_MATH_QUANT",
        "HOW_TO_TROUBLESHOOT",
        "CODING_TECH",
    }

def _cheap_primary_for_intent(intent: str, plan: Dict[str, Any]) -> str:
    # Minor overrides for quality/cost balance
    if intent == "LIVE_FRESH":
        return "PERPLEXITY"
    if intent == "WEB_RESEARCH_CITATIONS":
        return "PERPLEXITY"
    return plan.get("provider_primary") or "OPENAI"

def _fallback_chain_for_intent(intent: str, plan: Dict[str, Any]) -> List[str]:
    # Curated fallback chains (cost-aware) to avoid expensive “ranker always”
    if intent == "LIVE_FRESH":
        # Perplexity first, Grok second; avoid OpenAI “can't browse” UX
        return ["GROK", "GEMINI"]
    if intent == "WEB_RESEARCH_CITATIONS":
        return ["GEMINI", "OPENAI", "CLAUDE"]
    if intent == "CODING_TECH":
        # Use Claude as "repair/fallback", not default
        return ["CLAUDE"]

    # NEW: safety net for common intents (fixes “first request fails”)
    defaults = ["GEMINI", "PERPLEXITY"]  # pick whichever you actually have keys for
    return plan.get("provider_fallbacks") or defaults

def _primary_token_budget(intent: str, requested: int) -> int:
    requested = int(requested or PRIMARY_MAX_TOKENS_DEFAULT)
    if intent == "LIVE_FRESH":
        return max(min(requested, 1600), LIVE_FRESH_PRIMARY_MAX_TOKENS)
    if intent == "WEB_RESEARCH_CITATIONS":
        return max(min(requested, 1600), WEB_CITE_PRIMARY_MAX_TOKENS)
    return max(64, min(requested, 1400))

def _secondary_token_budget(intent: str, primary_budget: int) -> int:
    # Secondary is intentionally smaller
    if intent in ("LIVE_FRESH", "WEB_RESEARCH_CITATIONS"):
        return max(200, min(500, int(primary_budget * 0.5)))
    return SECONDARY_MAX_TOKENS_DEFAULT

def _needs_escalation(intent: str, answer: str, features: Dict[str, bool]) -> bool:
    """
    Escalate only when:
    - refusal/stall detected (esp. LIVE_FRESH)
    - citations asked, but answer lacks obvious citations
    - too short / looks truncated
    - coding tech and answer looks incomplete
    """
    if not answer or len(answer.strip()) < 40:
        return True

    # NEW: if the query is freshness-required, treat cutoff disclaimers as refusal
    # (prevents stale "as of my last knowledge update" reaching UI)
    if intent == "LIVE_FRESH" and _looks_like_refusal(answer):
        return True

    if intent == "WEB_RESEARCH_CITATIONS" or features.get("citations", False):
        # heuristic: if no URLs and no bracketed citations and no "Source"
        al = answer.lower()
        has_url = ("http://" in al) or ("https://" in al) or ("www." in al)
        has_bracket_cites = bool(re.search(r"\[\d+\]", answer))
        has_source_word = ("source" in al) or ("sources" in al) or ("according to" in al)
        if not (has_url or has_bracket_cites or has_source_word):
            return True

    # if answer ends abruptly (common truncation signal)
    if answer.strip().endswith(("...", "…")):
        return True

    return False

def _should_run_ranker(compare: bool, ans_a: str, ans_b: str) -> bool:
    # Only run ranker if user explicitly asked compare AND both are non-trivial and not refusal-like
    if not compare:
        return False
    if not ans_a or not ans_b:
        return False
    if len(ans_a.strip()) < 80 or len(ans_b.strip()) < 80:
        return False
    if _looks_like_refusal(ans_a) or _looks_like_refusal(ans_b):
        return False
    return True


async def run_pipeline(
    query: str,
    session_id: str | None,
    user_id=None,
    compare: bool = False,
    max_tokens: int = PRIMARY_MAX_TOKENS_DEFAULT,
    conversation: Optional[List[Dict[str, str]]] = None,
    memory: str = "",
    state: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    query_uuid = uuid.uuid4()

    features = extract_features(query)

    # NEW: promote office-holder/time-sensitive queries into freshness path even if keywords missed
    if _freshness_required(query, features):
        features["freshness"] = True  # helps pre_route + downstream behavior

    pre = pre_route(features, query)

    db = get_session()

    # Create query row (commit so billing counters can see it)
    if db:
        try:
            dbrepo.create_query(
                db,
                query_id=query_uuid,
                session_id=session_id,
                query_text=query,
                response_mode="text",
                features_json=features,
                pre_intent_hint=pre.get("pre_intent_hint"),
            )
            _safe_db_commit(db)
        except Exception:
            _safe_db_rollback(db)

    # Decide plan (pre-router hints override router; router still used for everything else)
    if pre.get("short_circuit"):
        intent_hint = pre.get("pre_intent_hint")

        if intent_hint == "LIVE_FRESH":
            plan = {
                "intent": intent_hint,
                "provider_primary": "PERPLEXITY",
                "provider_secondary": "GROK",
                "provider_fallbacks": ["GEMINI"],
                "confidence": 0.78,
                "multi_call": True,  # hint only; we gate by compare below
                "reason_codes": pre.get("pre_reason_codes", []),
            }
        elif intent_hint == "WEB_RESEARCH_CITATIONS":
            plan = {
                "intent": intent_hint,
                "provider_primary": "PERPLEXITY",
                "provider_secondary": "GEMINI",
                "provider_fallbacks": ["OPENAI", "CLAUDE"],
                "confidence": 0.78,
                "multi_call": True,
                "reason_codes": pre.get("pre_reason_codes", []),
            }
        elif intent_hint == "LOCAL_NEAR_ME":
            plan = {
                "intent": intent_hint,
                "provider_primary": "PERPLEXITY",
                "provider_secondary": "GEMINI",
                "provider_fallbacks": ["OPENAI"],
                "confidence": 0.72,
                "multi_call": True,
                "reason_codes": pre.get("pre_reason_codes", []),
            }
        elif intent_hint == "CODING_TECH":
            plan = {
                "intent": intent_hint,
                "provider_primary": "OPENAI",
                "provider_secondary": "CLAUDE",
                "provider_fallbacks": [],
                "confidence": 0.80,
                "multi_call": True,
                "reason_codes": pre.get("pre_reason_codes", []),
            }
        else:
            plan = await route_query(query, features)
    else:
        plan = await route_query(query, features)

    intent = plan["intent"]
    confidence = float(plan.get("confidence", 0.5))

    providers_called: List[str] = []
    today_utc = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Build normalized messages with deterministic conversation state
    messages = _build_messages(
        query=query,
        intent=intent,
        conversation=conversation,
        memory=memory,
        today_utc=today_utc,
    )

    # Token budgets (cost controls)
    primary_budget = _primary_token_budget(intent, max_tokens)

    meta: Dict[str, Any] = {
        "query_id": str(query_uuid),
        "session_id": session_id,
        "user_id": str(user_id) if user_id else None,
        "features": features,
        "plan": plan,
        "today_utc": today_utc,
        "max_tokens": int(primary_budget),
        "compare": bool(compare),
        "messages": messages,
        "memory": memory,
        "citations": [],
    }

    if state and isinstance(state, dict):
        meta["state"] = state

    # ----------------------------
    # CHEAP PATH (default): single call + escalation only if needed
    # ----------------------------
    force_single = _force_single_call(intent)
    if force_single or not compare:
        provider_primary = _cheap_primary_for_intent(intent, plan)
        fallbacks = _fallback_chain_for_intent(intent, plan)

        answer = None
        provider_used = "NONE"
        errors: List[str] = []

        # Build candidate list with primary first
        candidates = [provider_primary] + [p for p in fallbacks if p != provider_primary]

        # For LIVE_FRESH, don't ever call OpenAI/Claude first (avoid “can't browse” UX)
        if intent == "LIVE_FRESH":
            candidates = [p for p in candidates if p in ("PERPLEXITY", "GROK", "GEMINI")]

        for idx, p in enumerate(candidates):
            if not is_provider_available(p):
                errors.append(f"{p}:COOLDOWN")
                continue

            # Lower token budget on fallbacks
            if idx == 0:
                meta["max_tokens"] = int(primary_budget)
            else:
                meta["max_tokens"] = int(_secondary_token_budget(intent, primary_budget))

            try:
                providers_called.append(p)
                ans_try = await call_provider_logged(db, query_uuid, p, query, intent, meta)

                # Decide if we should accept or escalate
                if _needs_escalation(intent, ans_try, features):
                    errors.append(f"{p}:ESCALATE")
                    continue

                answer = ans_try
                provider_used = p
                break

            except ProviderError as e:
                errors.append(f"{p}:{type(e).__name__}:{str(e)[:160]}")
                if _is_rate_limit_error(e):
                    cooldown_provider(p, minutes=10)
                continue
            except Exception as e:
                errors.append(f"{p}:{type(e).__name__}:{str(e)[:160]}")
                if _is_rate_limit_error(e):
                    cooldown_provider(p, minutes=10)
                continue

        if answer is None:
            answer = "Sorry — providers are not configured or are temporarily unavailable."

        latency_total_ms = int((time.perf_counter() - t0) * 1000)

        if db:
            try:
                dbrepo.update_query_result(
                    db,
                    query_id=query_uuid,
                    router_intent=intent,
                    router_confidence=confidence,
                    multi_call=False,
                    providers_called_json=providers_called,
                    provider_used_final=provider_used,
                    latency_total_ms=latency_total_ms,
                    token_cost_estimate_usd=None,
                    answered=True,
                    meta_json={"features": features, "router": plan, "errors": errors},
                )
                _safe_db_commit(db)
            except Exception:
                _safe_db_rollback(db)

        _safe_db_close(db)

        return {
            "query_id": str(query_uuid),
            "answer": answer,
            "intent": intent,
            "provider_used": provider_used,
            "providers_called": providers_called,
            "confidence": confidence,
            "multi_call": False,
            "citations": meta.get("citations", []),
            "meta": {"features": features, "router": plan, "errors": errors},
        }

    # ----------------------------
    # PAID/PREMIUM PATH: compare=true
    # Multi-call (two providers) then rank (only if both good)
    # ----------------------------
    provider_primary = _cheap_primary_for_intent(intent, plan)
    provider_secondary = plan.get("provider_secondary") or (plan.get("provider_fallbacks") or [provider_primary])[0]
    fallbacks = _fallback_chain_for_intent(intent, plan)

    # For LIVE_FRESH compare, only allow Perplexity/Grok/Gemini
    pool = [provider_primary, provider_secondary] + [
        p for p in fallbacks if p not in (provider_primary, provider_secondary)
    ]
    if intent == "LIVE_FRESH":
        pool = [p for p in pool if p in ("PERPLEXITY", "GROK", "GEMINI")]

    chosen: List[str] = []
    for p in pool:
        if is_provider_available(p) and p not in chosen:
            chosen.append(p)
        if len(chosen) == 2:
            break
    if len(chosen) == 1:
        chosen.append(chosen[0])

    a_provider, b_provider = chosen[0], chosen[1]

    ans_a = ""
    ans_b = ""
    errors: List[str] = []

    # A = primary budget, B = secondary budget (cheaper)
    for p, slot in [(a_provider, "A"), (b_provider, "B")]:
        if not is_provider_available(p):
            errors.append(f"{p}:COOLDOWN")
            continue
        meta["max_tokens"] = int(primary_budget if slot == "A" else _secondary_token_budget(intent, primary_budget))
        try:
            providers_called.append(p)
            if slot == "A":
                ans_a = await call_provider_logged(db, query_uuid, p, query, intent, meta)
                if _needs_escalation(intent, ans_a, features):
                    errors.append(f"{p}:WEAK")
                    ans_a = ""
            else:
                ans_b = await call_provider_logged(db, query_uuid, p, query, intent, meta)
                if _needs_escalation(intent, ans_b, features):
                    errors.append(f"{p}:WEAK")
                    ans_b = ""
        except Exception as e:
            errors.append(f"{p}:{type(e).__name__}:{str(e)[:160]}")
            if _is_rate_limit_error(e):
                cooldown_provider(p, minutes=10)

    citations_requested = bool(features.get("citations", False))

    if _should_run_ranker(compare=True, ans_a=ans_a, ans_b=ans_b):
        ranked = await rank_answers(query, intent, citations_requested, a_provider, ans_a, b_provider, ans_b)
        final_answer = ranked.get("final_answer") or ""
        provider_used = f"{a_provider}+{b_provider}:{ranked.get('selection')}"
        ranker_meta = ranked
    else:
        ranked = None
        ranker_meta = None
        final_answer = ans_a or ans_b or "Sorry — I couldn't produce an answer."
        provider_used = a_provider if ans_a else (b_provider if ans_b else "NONE")

    latency_total_ms = int((time.perf_counter() - t0) * 1000)

    if db:
        try:
            dbrepo.update_query_result(
                db,
                query_id=query_uuid,
                router_intent=intent,
                router_confidence=confidence,
                multi_call=True,
                providers_called_json=providers_called,
                provider_used_final=provider_used,
                latency_total_ms=latency_total_ms,
                token_cost_estimate_usd=None,
                answered=True,
                meta_json={"features": features, "router": plan, "ranker": ranker_meta, "errors": errors},
            )
            _safe_db_commit(db)
        except Exception:
            _safe_db_rollback(db)

    _safe_db_close(db)

    return {
        "query_id": str(query_uuid),
        "answer": final_answer,
        "intent": intent,
        "provider_used": provider_used,
        "providers_called": providers_called,
        "confidence": confidence,
        "multi_call": True,
        "citations": meta.get("citations", []),
        "meta": {"features": features, "router": plan, "ranker": ranked, "errors": errors},
    }
