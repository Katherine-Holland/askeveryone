from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from app.db.models import QueryLog, ProviderCall

def create_query(
    db: Session,
    *,
    query_id,
    session_id: str | None,
    query_text: str,
    response_mode: str,
    features_json: dict | None,
    pre_intent_hint: str | None,
) -> QueryLog:
    q = QueryLog(
        query_id=query_id,
        session_id=session_id,
        query_text=query_text,
        response_mode=response_mode,
        features_json=features_json,
        pre_intent_hint=pre_intent_hint,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q

def update_query_result(
    db: Session,
    *,
    query_id,
    router_intent: str | None,
    router_confidence: float | None,
    multi_call: bool,
    providers_called_json: list | None,
    provider_used_final: str | None,
    latency_total_ms: int | None,
    token_cost_estimate_usd: float | None,
    answered: bool,
    meta_json: dict | None,
):
    q = db.get(QueryLog, query_id)
    if not q:
        return

    q.router_intent = router_intent
    q.router_confidence = router_confidence
    q.multi_call = multi_call
    q.providers_called_json = providers_called_json
    q.provider_used_final = provider_used_final
    q.latency_total_ms = latency_total_ms
    q.token_cost_estimate_usd = token_cost_estimate_usd
    q.answered = answered
    q.meta_json = meta_json

    db.commit()

def create_provider_call(db: Session, *, query_id, provider: str) -> ProviderCall:
    pc = ProviderCall(
        query_id=query_id,
        provider=provider,
        success=False,
        started_at=datetime.utcnow(),
    )
    db.add(pc)
    db.commit()
    db.refresh(pc)
    return pc

def finish_provider_call(
    db: Session,
    *,
    call_id,
    success: bool,
    latency_ms: int | None,
    error_code: str | None = None,
    answer_excerpt: str | None = None,
    token_in: int | None = None,
    token_out: int | None = None,
    cost_estimate_usd: float | None = None,
):
    pc = db.get(ProviderCall, call_id)
    if not pc:
        return

    pc.ended_at = datetime.utcnow()
    pc.success = success
    pc.latency_ms = latency_ms
    pc.error_code = error_code
    pc.answer_excerpt = answer_excerpt
    pc.token_in = token_in
    pc.token_out = token_out
    pc.cost_estimate_usd = cost_estimate_usd

    db.commit()
