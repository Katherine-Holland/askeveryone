# app/orchestrator.py
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

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


def _safe_db_close(db) -> None:
    try:
        if db:
            db.close()
    except Exception:
        pass


def _format_state_for_prompt(state: Dict[str, Any]) -> str:
    """
    Deterministic, low-drift representation of conversation state.
    """
    if not state:
        return ""

    lines: List[str] = []
    topic = (state.get("topic") or "").strip()
    if topic:
        lines.append(f"Topic: {topic}")

    # Entities (destination, location, project, etc.)
    entities = state.get("entities") or {}
    if isinstance(entities, dict) and entities:
        pairs = []
        for k, v in entities.items():
            if v is None:
                continue
            sv = str(v).strip()
            if sv:
                pairs.append(f"{k}={sv}")
        if pairs:
            lines.append("Entities: " + ", ".join(pairs))

    # Facts
    facts = state.get("facts") or []
    if isinstance(facts, list) and facts:
        facts_clean = [str(x).strip() for x in facts if str(x).strip()]
        if facts_clean:
            lines.append("Known facts:")
            for f in facts_clean[:8]:
                lines.append(f"- {f}")

    # User preferences (style, constraints)
    prefs = state.get("preferences") or []
    if isinstance(prefs, list) and prefs:
        prefs_clean = [str(x).strip() for x in prefs if str(x).strip()]
        if prefs_clean:
            lines.append("Preferences:")
            for p in prefs_clean[:8]:
                lines.append(f"- {p}")

    # Open threads / questions
    openq = state.get("open_questions") or []
    if isinstance(openq, list) and openq:
        oq = [str(x).strip() for x in openq if str(x).strip()]
        if oq:
            lines.append("Open threads:")
            for q in oq[:6]:
                lines.append(f"- {q}")

    return "\n".join(lines).strip()


def _build_messages(
    *,
    query: str,
    intent: str,
    conversation: Optional[List[Dict[str, str]]] = None,
    state: Optional[Dict[str, Any]] = None,
    today_utc: str = "",
) -> List[Dict[str, str]]:
    """
    Build a single normalized conversation payload usable by all providers.
    Providers SHOULD prefer meta["messages"] over constructing their own prompt.
    """
    msgs: List[Dict[str, str]] = []

    system_lines = [
        "You are Seekle, a helpful assistant.",
        "You must answer follow-up questions using the conversation context.",
        "Do NOT ask the user 'where are you going?' if the destination is in the conversation state or recent messages.",
        "If context is truly missing, ask ONE concise clarification question.",
    ]
    if today_utc:
        system_lines.append(f"Today's date (UTC): {today_utc}")

    # Conversation state comes first (deterministic)
    state_text = _format_state_for_prompt(state or {})
    if state_text:
        msgs.append({"role": "system", "content": "Conversation State (authoritative):\n" + state_text})

    # Main system instruction
    msgs.append({"role": "system", "content": "\n".join(system_lines)})

    # Prior conversation (oldest -> newest)
    if conversation:
        for m in conversation:
            role = (m.get("role") or "").strip()
            content = (m.get("content") or "").strip()
            if not role or not content:
                continue
            if role not in ("user", "assistant", "system"):
                role = "user"
            msgs.append({"role": role, "content": content})

    # Current user turn last
    msgs.append({"role": "user", "content": query.strip()})

    return msgs


async def call_provider(provider_name: str, query: str, intent: str, meta: Dict[str, Any]) -> str:
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ProviderError(f"Provider not implemented: {provider_name}")
    return await provider.ask(query=query, intent=intent, meta=meta)


async def call_provider_logged(db, query_uuid, provider_name: str, query: str, intent: str, meta: Dict[str, Any]) -> str:
    pc_id = None
    start = time.perf_counter()

    if db:
        try:
            pc = dbrepo.create_provider_call(db, query_id=query_uuid, provider=provider_name)
            pc_id = pc.call_id
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
                    error_code="ProviderError",
                )
            except Exception:
                _safe_db_rollback(db)
        raise


async def run_pipeline(
    query: str,
    session_id: str | None,
    user_id=None,
    compare: bool = False,
    max_tokens: int = 500,
    conversation: Optional[List[Dict[str, str]]] = None,
    state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    query_uuid = uuid.uuid4()

    features = extract_features(query)
    pre = pre_route(features, query)

    db = get_session()

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
        except Exception:
            _safe_db_rollback(db)

    if pre.get("short_circuit"):
        intent_hint = pre.get("pre_intent_hint")
        if intent_hint == "LIVE_FRESH":
            plan = {"intent": intent_hint, "provider_primary": "GROK", "provider_secondary": "PERPLEXITY",
                    "provider_fallbacks": ["GEMINI", "OPENAI"], "confidence": 0.75, "multi_call": True,
                    "reason_codes": pre.get("pre_reason_codes", [])}
        elif intent_hint == "WEB_RESEARCH_CITATIONS":
            plan = {"intent": intent_hint, "provider_primary": "PERPLEXITY", "provider_secondary": "GEMINI",
                    "provider_fallbacks": ["OPENAI", "CLAUDE"], "confidence": 0.78, "multi_call": True,
                    "reason_codes": pre.get("pre_reason_codes", [])}
        elif intent_hint == "LOCAL_NEAR_ME":
            plan = {"intent": intent_hint, "provider_primary": "PERPLEXITY",
                    "provider_secondary": "GEMINI" if pre.get("pre_multi_call_hint") else None,
                    "provider_fallbacks": ["OPENAI"], "confidence": 0.72,
                    "multi_call": bool(pre.get("pre_multi_call_hint")),
                    "reason_codes": pre.get("pre_reason_codes", [])}
        elif intent_hint == "CODING_TECH":
            plan = {"intent": intent_hint, "provider_primary": "OPENAI",
                    "provider_secondary": "CLAUDE" if pre.get("pre_multi_call_hint") else None,
                    "provider_fallbacks": [], "confidence": 0.80,
                    "multi_call": bool(pre.get("pre_multi_call_hint")),
                    "reason_codes": pre.get("pre_reason_codes", [])}
        else:
            plan = await route_query(query, features)
    else:
        plan = await route_query(query, features)

    intent = plan["intent"]
    provider_primary = plan["provider_primary"]
    provider_secondary = plan.get("provider_secondary")
    fallbacks = plan.get("provider_fallbacks", [])
    confidence = float(plan.get("confidence", 0.5))
    multi_call = bool(plan.get("multi_call", False))

    if not compare:
        multi_call = False

    providers_called: List[str] = []
    today_utc = datetime.now(timezone.utc).strftime("%B %d, %Y")

    messages = _build_messages(
        query=query,
        intent=intent,
        conversation=conversation,
        state=state,
        today_utc=today_utc,
    )

    meta = {
        "query_id": str(query_uuid),
        "session_id": session_id,
        "user_id": str(user_id) if user_id else None,
        "features": features,
        "plan": plan,
        "today_utc": today_utc,
        "max_tokens": int(max_tokens),
        "compare": bool(compare),
        "messages": messages,   # ✅ Consistent multi-turn input
        "state": state or {},   # ✅ Deterministic memory/state
    }

    # -------- Single call + fallbacks --------
    if not multi_call:
        answer = None
        provider_used = "NONE"
        errors: List[str] = []

        for p in [provider_primary] + fallbacks:
            if not is_provider_available(p):
                continue
            try:
                providers_called.append(p)
                answer = await call_provider_logged(db, query_uuid, p, query, intent, meta)
                provider_used = p
                break
            except ProviderError as e:
                errors.append(f"{p}:{type(e).__name__}:{str(e)[:160]}")
                if _is_rate_limit_error(e):
                    cooldown_provider(p, minutes=10)
            except Exception as e:
                errors.append(f"{p}:{type(e).__name__}:{str(e)[:160]}")
                if _is_rate_limit_error(e):
                    cooldown_provider(p, minutes=10)

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
                    multi_call=multi_call,
                    providers_called_json=providers_called,
                    provider_used_final=provider_used,
                    latency_total_ms=latency_total_ms,
                    token_cost_estimate_usd=None,
                    answered=True,
                    meta_json={"features": features, "router": plan, "errors": errors},
                )
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
            "multi_call": multi_call,
            "meta": {"features": features, "router": plan, "errors": errors},
        }

    # -------- Multi-call (compare) then rank --------
    a_provider = provider_primary
    b_provider = provider_secondary or (fallbacks[0] if fallbacks else provider_primary)

    ans_a = ""
    ans_b = ""
    errors = []

    pool = [a_provider, b_provider] + [p for p in fallbacks if p not in [a_provider, b_provider]]
    chosen: List[str] = []
    for p in pool:
        if is_provider_available(p) and p not in chosen:
            chosen.append(p)
        if len(chosen) == 2:
            break
    if len(chosen) == 1:
        chosen.append(b_provider)

    a_provider, b_provider = chosen[0], chosen[1]

    for p, slot in [(a_provider, "A"), (b_provider, "B")]:
        if not is_provider_available(p):
            errors.append(f"{p}:COOLDOWN")
            continue
        try:
            providers_called.append(p)
            if slot == "A":
                ans_a = await call_provider_logged(db, query_uuid, p, query, intent, meta)
            else:
                ans_b = await call_provider_logged(db, query_uuid, p, query, intent, meta)
        except Exception as e:
            errors.append(f"{p}:{type(e).__name__}:{str(e)[:160]}")
            if _is_rate_limit_error(e):
                cooldown_provider(p, minutes=10)

    citations_requested = bool(features.get("citations", False))

    if ans_a and ans_b:
        ranked = await rank_answers(query, intent, citations_requested, a_provider, ans_a, b_provider, ans_b)
        final_answer = ranked.get("final_answer") or ""
        provider_used = f"{a_provider}+{b_provider}:{ranked.get('selection')}"

        latency_total_ms = int((time.perf_counter() - t0) * 1000)

        if db:
            try:
                dbrepo.update_query_result(
                    db,
                    query_id=query_uuid,
                    router_intent=intent,
                    router_confidence=confidence,
                    multi_call=multi_call,
                    providers_called_json=providers_called,
                    provider_used_final=provider_used,
                    latency_total_ms=latency_total_ms,
                    token_cost_estimate_usd=None,
                    answered=True,
                    meta_json={"features": features, "router": plan, "ranker": ranked, "errors": errors},
                )
            except Exception:
                _safe_db_rollback(db)

        _safe_db_close(db)

        return {
            "query_id": str(query_uuid),
            "answer": final_answer or "Sorry — I couldn't produce an answer.",
            "intent": intent,
            "provider_used": provider_used,
            "providers_called": providers_called,
            "confidence": confidence,
            "multi_call": multi_call,
            "meta": {"features": features, "router": plan, "ranker": ranked, "errors": errors},
        }

    fallback_answer = ans_a or ans_b or "Sorry — providers are not configured or are temporarily unavailable."
    provider_used = a_provider if ans_a else b_provider if ans_b else "NONE"

    _safe_db_close(db)

    return {
        "query_id": str(query_uuid),
        "answer": fallback_answer,
        "intent": intent,
        "provider_used": provider_used,
        "providers_called": providers_called,
        "confidence": confidence,
        "multi_call": multi_call,
        "meta": {"features": features, "router": plan, "errors": errors},
    }
