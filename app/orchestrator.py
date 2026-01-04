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

# IMPORTANT: Do NOT import optional providers unless you really need them.
# They can break deploys if dependencies / env aren’t present.
# from app.providers.huggingface_provider import HuggingFaceProvider
# from app.providers.llama_provider import LlamaProvider

from app.providers.base import ProviderError
from app.config import settings

from app.db.session import get_session
from app.db import repo as dbrepo

from app.limits import cooldown_provider, is_provider_available


def _is_rate_limit_error(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "429" in msg
        or "rate limit" in msg
        or "quota" in msg
        or "too many requests" in msg
        or "resource exhausted" in msg
    )


def provider_is_configured(name: str) -> bool:
    """
    Prevents the orchestrator from calling providers whose env vars are missing.
    This avoids 'Provider not configured' failures causing provider_used=NONE.
    """
    name = (name or "").upper()
    if name == "OPENAI":
        return bool(settings.openai_api_key)
    if name == "CLAUDE":
        return bool(settings.anthropic_api_key)
    if name == "GROK":
        return bool(settings.grok_api_key)
    if name == "GEMINI":
        return bool(settings.gemini_api_key)
    if name == "PERPLEXITY":
        return bool(settings.perplexity_api_key)
    if name == "LLAMA":
        return bool(settings.llama_api_key and settings.llama_base_url)
    if name == "HUGGINGFACE":
        return bool(settings.huggingface_api_key)
    return False


# Only register providers that should exist in this deploy.
# (You can add LLAMA/HF back later once Together/etc is stable.)
PROVIDERS = {
    "OPENAI": OpenAIProvider(),
    "PERPLEXITY": PerplexityProvider(),
    "GROK": GrokProvider(),
    "CLAUDE": ClaudeProvider(),
    "GEMINI": GeminiProvider(),
    # "LLAMA": LlamaProvider(),
    # "HUGGINGFACE": HuggingFaceProvider(),
}


async def call_provider(provider_name: str, query: str, intent: str, meta: Dict[str, Any]) -> str:
    provider_name = (provider_name or "").upper()

    if not provider_is_configured(provider_name):
        raise ProviderError(f"{provider_name} not configured (missing API key/base_url)")

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
        pc = dbrepo.create_provider_call(db, query_id=query_uuid, provider=provider_name)
        pc_id = pc.call_id

    try:
        answer = await call_provider(provider_name, query, intent, meta)
        latency_ms = int((time.perf_counter() - start) * 1000)

        if db and pc_id:
            excerpt = (answer[:300] + "…") if len(answer) > 300 else answer
            dbrepo.finish_provider_call(
                db,
                call_id=pc_id,
                success=True,
                latency_ms=latency_ms,
                answer_excerpt=excerpt,
            )
        return answer

    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        if db and pc_id:
            dbrepo.finish_provider_call(
                db,
                call_id=pc_id,
                success=False,
                latency_ms=latency_ms,
                error_code=f"{type(e).__name__}:{str(e)[:120]}",
            )
        raise


def _candidate_providers(primary: str, fallbacks: List[str]) -> List[str]:
    """
    Build a final ordered list:
    - only configured providers
    - only those not on cooldown
    - preserve order
    """
    out: List[str] = []
    for p in [primary] + (fallbacks or []):
        p = (p or "").upper()
        if not p:
            continue
        if p in out:
            continue
        if not provider_is_configured(p):
            continue
        if not is_provider_available(p):
            continue
        out.append(p)
    return out


async def run_pipeline(
    query: str,
    session_id: str | None,
    user_id=None,
    compare: bool = False,
    max_tokens: int = 500,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    query_uuid = uuid.uuid4()

    features = extract_features(query)
    pre = pre_route(features, query)

    db = None
    try:
        db = get_session()
    except Exception:
        db = None

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
            pass

    # Decide routing plan (your current logic preserved)
    if pre.get("short_circuit"):
        intent_hint = pre.get("pre_intent_hint")

        if intent_hint == "LIVE_FRESH":
            plan = {
                "intent": intent_hint,
                "provider_primary": "GROK",
                "provider_secondary": "PERPLEXITY",
                "provider_fallbacks": ["GEMINI", "OPENAI"],
                "confidence": 0.75,
                "multi_call": True,
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
                "provider_secondary": "GEMINI" if pre.get("pre_multi_call_hint") else None,
                "provider_fallbacks": ["OPENAI"],
                "confidence": 0.72,
                "multi_call": bool(pre.get("pre_multi_call_hint")),
                "reason_codes": pre.get("pre_reason_codes", []),
            }
        else:
            plan = await route_query(query, features)
    else:
        plan = await route_query(query, features)

    intent = plan["intent"]
    provider_primary = (plan["provider_primary"] or "").upper()
    provider_secondary = (plan.get("provider_secondary") or "").upper() or None
    fallbacks = [str(p).upper() for p in plan.get("provider_fallbacks", [])]
    confidence = float(plan.get("confidence", 0.5))
    multi_call = bool(plan.get("multi_call", False))

    # Hard rule: multi-call only if user explicitly requested compare
    if not compare:
        multi_call = False

    today_utc = datetime.now(timezone.utc).strftime("%B %d, %Y")
    meta = {
        "query_id": str(query_uuid),
        "session_id": session_id,
        "user_id": str(user_id) if user_id else None,
        "features": features,
        "plan": plan,
        "today_utc": today_utc,
        "max_tokens": int(max_tokens),
        "compare": bool(compare),
    }

    providers_called: List[str] = []
    errors: List[str] = []

    # -------------------
    # SINGLE CALL
    # -------------------
    if not multi_call:
        candidates = _candidate_providers(provider_primary, fallbacks)

        # As a safety net, if router picked something not configured,
        # try a minimal "known good" set in order.
        if not candidates:
            fallback_safe = ["OPENAI", "CLAUDE", "GROK", "PERPLEXITY", "GEMINI"]
            candidates = [p for p in fallback_safe if provider_is_configured(p) and is_provider_available(p)]

        answer: Optional[str] = None
        provider_used = "NONE"

        for p in candidates:
            try:
                providers_called.append(p)
                answer = await call_provider_logged(db, query_uuid, p, query, intent, meta)
                provider_used = p
                break
            except ProviderError as e:
                errors.append(f"{p}:{type(e).__name__}:{str(e)[:120]}")
                if _is_rate_limit_error(e):
                    cooldown_provider(p, minutes=10)
                continue
            except Exception as e:
                errors.append(f"{p}:{type(e).__name__}:{str(e)[:120]}")
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
                    multi_call=multi_call,
                    providers_called_json=providers_called,
                    provider_used_final=provider_used,
                    latency_total_ms=latency_total_ms,
                    token_cost_estimate_usd=None,
                    answered=True,
                    meta_json={"features": features, "router": plan, "errors": errors},
                )
            except Exception:
                pass
            db.close()

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

    # -------------------
    # MULTI-CALL (COMPARE)
    # -------------------
    pool = [provider_primary]
    if provider_secondary:
        pool.append(provider_secondary)
    pool += [p for p in fallbacks if p not in pool]

    # filter pool (configured + not cooldown)
    pool = [p for p in pool if provider_is_configured(p) and is_provider_available(p)]

    # safety fallback if pool empty
    if not pool:
        pool = [p for p in ["OPENAI", "CLAUDE", "PERPLEXITY", "GROK", "GEMINI"] if provider_is_configured(p) and is_provider_available(p)]

    a_provider = pool[0]
    b_provider = pool[1] if len(pool) > 1 else pool[0]

    ans_a = ""
    ans_b = ""

    for p, slot in [(a_provider, "A"), (b_provider, "B")]:
        try:
            providers_called.append(p)
            if slot == "A":
                ans_a = await call_provider_logged(db, query_uuid, p, query, intent, meta)
            else:
                ans_b = await call_provider_logged(db, query_uuid, p, query, intent, meta)
        except Exception as e:
            errors.append(f"{p}:{type(e).__name__}:{str(e)[:120]}")
            if _is_rate_limit_error(e):
                cooldown_provider(p, minutes=10)

    citations_requested = bool(features.get("citations", False))

    if ans_a and ans_b:
        ranked = await rank_answers(query, intent, citations_requested, a_provider, ans_a, b_provider, ans_b)
        final_answer = ranked["final_answer"] if not ranked.get("needs_followup") else ranked.get("followup_question", "")
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
                pass
            db.close()

        return {
            "query_id": str(query_uuid),
            "answer": final_answer,
            "intent": intent,
            "provider_used": provider_used,
            "providers_called": providers_called,
            "confidence": confidence,
            "multi_call": multi_call,
            "meta": {"features": features, "router": plan, "ranker": ranked, "errors": errors},
        }

    # fallback if multi-call failed
    fallback_answer = ans_a or ans_b or "Sorry — providers are not configured or are temporarily unavailable."
    provider_used = a_provider if ans_a else b_provider if ans_b else "NONE"

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
            pass
        db.close()

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
