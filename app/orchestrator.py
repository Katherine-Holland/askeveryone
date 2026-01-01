import time
import uuid
from typing import Dict, Any, List

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


PROVIDERS = {
    "OPENAI": OpenAIProvider(),
    "PERPLEXITY": PerplexityProvider(),
    "GROK": GrokProvider(),
    "CLAUDE": ClaudeProvider(),
    "GEMINI": GeminiProvider(),
    "LLAMA": LlamaProvider(),
    "HUGGINGFACE": HuggingFaceProvider(),
}


async def call_provider(provider_name: str, query: str, intent: str, meta: Dict[str, Any]) -> str:
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ProviderError(f"Provider not implemented: {provider_name}")
    return await provider.ask(query=query, intent=intent, meta=meta)


async def call_provider_logged(db, query_uuid, provider_name: str, query: str, intent: str, meta: Dict[str, Any]) -> str:
    """
    Logs provider call start/end into Neon.
    If DB isn't configured, this behaves like call_provider().
    """
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
                error_code=type(e).__name__,
            )
        raise


async def run_pipeline(query: str, session_id: str | None) -> Dict[str, Any]:
    t0 = time.perf_counter()
    query_uuid = uuid.uuid4()

    features = extract_features(query)
    pre = pre_route(features, query)

    # DB session (optional)
    db = get_session()

    # Create initial query row in DB
    if db:
        dbrepo.create_query(
            db,
            query_id=query_uuid,
            session_id=session_id,
            query_text=query,
            response_mode="text",
            features_json=features,
            pre_intent_hint=pre.get("pre_intent_hint"),
        )

    # Decide routing plan
    if pre["short_circuit"]:
        intent_hint = pre["pre_intent_hint"]

        if intent_hint == "LIVE_FRESH":
            plan = {
                "intent": intent_hint,
                "provider_primary": "GROK",
                "provider_secondary": "PERPLEXITY",
                "provider_fallbacks": ["GEMINI", "OPENAI"],
                "confidence": 0.75,
                "multi_call": True,
                "reason_codes": pre["pre_reason_codes"],
            }
        elif intent_hint == "WEB_RESEARCH_CITATIONS":
            plan = {
                "intent": intent_hint,
                "provider_primary": "PERPLEXITY",
                "provider_secondary": "GEMINI",
                "provider_fallbacks": ["OPENAI", "CLAUDE"],
                "confidence": 0.78,
                "multi_call": True,
                "reason_codes": pre["pre_reason_codes"],
            }
        elif intent_hint == "LOCAL_NEAR_ME":
            plan = {
                "intent": intent_hint,
                "provider_primary": "PERPLEXITY",
                "provider_secondary": "GEMINI" if pre["pre_multi_call_hint"] else None,
                "provider_fallbacks": ["OPENAI"],
                "confidence": 0.72,
                "multi_call": bool(pre["pre_multi_call_hint"]),
                "reason_codes": pre["pre_reason_codes"],
            }
        elif intent_hint == "CODING_TECH":
            plan = {
                "intent": intent_hint,
                "provider_primary": "OPENAI",
                "provider_secondary": "CLAUDE" if pre["pre_multi_call_hint"] else None,
                "provider_fallbacks": ["LLAMA", "HUGGINGFACE"],
                "confidence": 0.80,
                "multi_call": bool(pre["pre_multi_call_hint"]),
                "reason_codes": pre["pre_reason_codes"],
            }
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

    providers_called: List[str] = []
    meta = {
        "query_id": str(query_uuid),
        "session_id": session_id,
        "features": features,
        "plan": plan,
    }

    # Execute
    if not multi_call:
        answer = None
        provider_used = "NONE"

        for p in [provider_primary] + fallbacks:
            try:
                providers_called.append(p)
                answer = await call_provider_logged(db, query_uuid, p, query, intent, meta)
                provider_used = p
                break
            except ProviderError:
                continue
            except Exception:
                continue

        if answer is None:
            answer = "Sorry — providers are not configured yet."

        latency_total_ms = int((time.perf_counter() - t0) * 1000)

        # Update query row
        if db:
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
                meta_json={"features": features, "router": plan},
            )
            db.close()

        return {
            "query_id": str(query_uuid),
            "answer": answer,
            "intent": intent,
            "provider_used": provider_used,
            "providers_called": providers_called,
            "confidence": confidence,
            "multi_call": multi_call,
            "meta": {"features": features, "router": plan},
        }

    # Multi-call: call top 2 then rank
    a_provider = provider_primary
    b_provider = provider_secondary or (fallbacks[0] if fallbacks else provider_primary)

    ans_a = ""
    ans_b = ""
    errors: List[str] = []

    for p, slot in [(a_provider, "A"), (b_provider, "B")]:
        try:
            providers_called.append(p)
            if slot == "A":
                ans_a = await call_provider_logged(db, query_uuid, p, query, intent, meta)
            else:
                ans_b = await call_provider_logged(db, query_uuid, p, query, intent, meta)
        except Exception as e:
            errors.append(f"{p}:{type(e).__name__}")

    citations_requested = bool(features.get("citations", False))

    if ans_a and ans_b:
        ranked = await rank_answers(query, intent, citations_requested, a_provider, ans_a, b_provider, ans_b)
        final_answer = ranked["final_answer"] if not ranked.get("needs_followup") else ranked.get("followup_question", "")
        provider_used = f"{a_provider}+{b_provider}:{ranked.get('selection')}"

        latency_total_ms = int((time.perf_counter() - t0) * 1000)

        if db:
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

    # Fallback if multi-call failed
    fallback_answer = ans_a or ans_b or "Sorry — providers are not configured yet."
    provider_used = a_provider if ans_a else b_provider if ans_b else "NONE"

    latency_total_ms = int((time.perf_counter() - t0) * 1000)

    if db:
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
