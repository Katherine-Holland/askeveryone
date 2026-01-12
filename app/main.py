# app/main.py
from __future__ import annotations

import re
import uuid
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.schemas import AskRequest, AskResponse
from app.orchestrator import run_pipeline
from app.config import settings
from app.db.session import init_engine, get_session

# limits + billing
from app.limits import daily_limit_for_user, max_tokens_for_tier
from app.db import billing_repo

# conversation + memory
from app.db import memory_repo

# anon gate
from app.security.anon_gate import (
    build_anon_key,
    anon_allowance_used_today,
    record_anon_use_today,
    anon_global_used_today,
    record_anon_global_use_today,
)

# Use ONE shared Base across all models
from app.db.base import Base

# IMPORTANT: import model modules so Base.metadata knows about all tables
import app.db.models
import app.db.models_auth
import app.db.models_billing
import app.db.models_memory  # ensures session_memory is created

# Routers
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.metrics import router as metrics_router
from app.api.diagnostics import router as diagnostics_router
from app.api.test_provider import router as test_provider_router
from app.api.billing import router as billing_router


app = FastAPI(title="AskEveryone (Seekle backend)")


def init_db():
    engine = init_engine()
    if engine is None:
        return
    Base.metadata.create_all(bind=engine)


@app.on_event("startup")
async def startup_event():
    init_db()


# ---------- Routers ----------
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(metrics_router)
app.include_router(diagnostics_router)
app.include_router(test_provider_router)
app.include_router(billing_router)


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


def _safe_rollback(db) -> None:
    try:
        if db:
            db.rollback()
    except Exception:
        pass


def _safe_commit(db) -> None:
    try:
        if db:
            db.commit()
    except Exception:
        _safe_rollback(db)
        raise


def _insert_message(db, *, session_id: str, role: str, content: str) -> None:
    try:
        db.execute(
            text(
                "insert into messages (message_id, session_id, role, content) "
                "values (:mid, :sid, :role, :content)"
            ),
            {"mid": uuid.uuid4(), "sid": session_id, "role": role, "content": content},
        )
        _safe_commit(db)
    except Exception:
        _safe_rollback(db)


def _norm_ua(ua: str | None) -> str:
    if not ua:
        return ""
    return " ".join(ua.strip().lower().split())[:300]


def _get_client_ip(request: Request) -> str | None:
    for hdr in ["cf-connecting-ip", "true-client-ip", "x-real-ip"]:
        v = request.headers.get(hdr)
        if v:
            return v.strip()

    xff = request.headers.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]

    return request.client.host if request.client else None


def _anon_session_used_today(db, session_id: str) -> int:
    row = db.execute(
        text(
            "select count(*) from queries "
            "where session_id=:sid "
            "and received_at >= (now() at time zone 'utc')::date"
        ),
        {"sid": session_id},
    ).fetchone()
    return int(row[0]) if row else 0


def _should_update_state(turn_count: int) -> bool:
    n = int(getattr(settings, "memory_update_every_n_turns", 2))
    if n <= 0:
        return False
    return (turn_count % n) == 0


# ----------------------------
# Phase 2B: Deterministic state extractor
# ----------------------------
_DEST_PATTERNS = [
    re.compile(r"\bmoon\b", re.I),
    re.compile(r"\bmars\b", re.I),
    re.compile(r"\bnew york\b", re.I),
    re.compile(r"\bcalifornia\b", re.I),
    re.compile(r"\beu\b", re.I),
]


def _extract_state_from_recent(recent_msgs, prev_state: dict | None = None) -> dict:
    """
    Rule-based, low-drift state update.
    Only uses actual transcript lines, never invents facts.
    """
    state = dict(prev_state or {})

    # initialize keys
    state.setdefault("topic", "")
    state.setdefault("entities", {})
    state.setdefault("facts", [])
    state.setdefault("preferences", [])
    state.setdefault("open_questions", [])

    entities = state.get("entities") or {}
    if not isinstance(entities, dict):
        entities = {}
    state["entities"] = entities

    # look at recent user messages
    user_texts = [m.get("content", "") for m in recent_msgs if m.get("role") == "user"]
    joined = "\n".join([t for t in user_texts if t]).strip()

    # Detect destination-like entity
    dest = entities.get("destination", "")
    if not dest:
        for pat in _DEST_PATTERNS:
            if pat.search(joined):
                entities["destination"] = pat.pattern.strip("\\b").replace("\\", "").replace("(?i)", "").upper()
                # Normalize a bit (moon/mars/etc)
                entities["destination"] = "moon" if "moon" in pat.pattern.lower() else entities["destination"].lower()
                break

    # Detect “coding / building” mode
    if "code" in joined.lower() or "build" in joined.lower() or "fastapi" in joined.lower():
        if not state.get("topic"):
            state["topic"] = "Building Seekle backend"
        # preference: systematic steps (you asked for one-at-a-time)
        pref = "User prefers step-by-step, one change at a time."
        if pref not in state["preferences"]:
            state["preferences"].append(pref)

    # If the user asks a follow-up “how long to get there”, mark as open thread
    if re.search(r"\bhow long\b", joined.lower()) and ("get there" in joined.lower() or "take" in joined.lower()):
        oq = "User asked for travel time to destination mentioned earlier."
        if oq not in state["open_questions"]:
            state["open_questions"].append(oq)

    # Keep lists bounded (prevent bloat)
    state["facts"] = (state.get("facts") or [])[:20]
    state["preferences"] = (state.get("preferences") or [])[:20]
    state["open_questions"] = (state.get("open_questions") or [])[:20]

    return state


@app.get("/diagnostics/openai_ping")
async def diagnostics_openai_ping():
    if not settings.openai_api_key:
        return {"ok": False, "error": "OPENAI_API_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            )
        return {"ok": r.status_code == 200, "status_code": r.status_code, "body_excerpt": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "detail": str(e)}


@app.get("/")
async def root():
    return {
        "service": "askeveryone",
        "status": "ok",
        "endpoints": [
            "/health",
            "/ask",
            "/chat/start",
            "/auth/request-link",
            "/auth/verify",
            "/diagnostics/providers",
            "/billing/status",
            "/billing/webhook/stripe",
            "/chat/export",
            "/chat/import",
        ],
    }


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request):
    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        if not req.session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        _safe_rollback(db)

        # Ensure session exists
        try:
            db.execute(
                text(
                    "insert into chat_sessions (session_id, is_anonymous) "
                    "values (:sid, true) on conflict (session_id) do nothing"
                ),
                {"sid": req.session_id},
            )
            _safe_commit(db)
        except Exception:
            _safe_rollback(db)
            raise HTTPException(status_code=500, detail="Failed to initialize session")

        # Resolve user_id
        user_id = None
        try:
            row = db.execute(
                text("select user_id from chat_sessions where session_id=:sid"),
                {"sid": req.session_id},
            ).fetchone()
            user_id = row[0] if row and row[0] else None
        except Exception:
            _safe_rollback(db)
            user_id = None

        # Load conversation + state
        history_limit = int(getattr(settings, "conversation_history_limit", 16))
        conversation = []
        state = {}
        try:
            conversation = memory_repo.get_recent_messages(db, req.session_id, limit=history_limit)
            state = memory_repo.get_state(db, req.session_id)
        except Exception:
            _safe_rollback(db)
            conversation = []
            state = {}

        # -------------------------
        # Anonymous gating
        # -------------------------
        if user_id is None:
            ip = _get_client_ip(request)
            ua = _norm_ua(request.headers.get("user-agent"))
            key_hash = build_anon_key(ip=ip, user_agent=ua)

            anon_global_cap = int(getattr(settings, "anon_global_pool_per_day", 200))
            anon_key_cap = int(getattr(settings, "anon_free_per_24h", 1))

            try:
                used_session_today = _anon_session_used_today(db, req.session_id)
            except Exception:
                _safe_rollback(db)
                used_session_today = 10**9

            anon_session_cap = int(getattr(settings, "anon_session_free_per_day", 2))
            if used_session_today >= anon_session_cap:
                raise HTTPException(
                    status_code=402,
                    detail="Create a free account to save your conversation and continue searching.",
                )

            try:
                used_global = anon_global_used_today(db)
            except Exception:
                _safe_rollback(db)
                used_global = 10**9

            if used_global >= anon_global_cap:
                raise HTTPException(
                    status_code=402,
                    detail="Free access is busy right now. Create a free account to continue and save your conversation.",
                )

            try:
                used_key = anon_allowance_used_today(db, key_hash)
            except Exception:
                _safe_rollback(db)
                used_key = 10**9

            if used_key >= anon_key_cap:
                raise HTTPException(
                    status_code=402,
                    detail="Create a free account to save your conversation and continue searching.",
                )

            try:
                record_anon_use_today(db, key_hash)
                record_anon_global_use_today(db)
                _safe_commit(db)
            except Exception:
                _safe_rollback(db)
                raise HTTPException(status_code=429, detail="Temporary protection triggered. Please create a free account to continue.")

            _insert_message(db, session_id=req.session_id, role="user", content=req.query)

            result = await run_pipeline(
                query=req.query,
                session_id=req.session_id,
                user_id=None,
                compare=bool(getattr(req, "compare", False)),
                max_tokens=max_tokens_for_tier(is_paid=False),
                conversation=conversation,
                state=state,
            )

            _insert_message(db, session_id=req.session_id, role="assistant", content=result.get("answer", ""))

        else:
            # -------------------------
            # Logged-in policy
            # -------------------------
            try:
                billing_repo.ensure_wallet_and_plan(db, user_id)
                plan = billing_repo.get_user_plan(db, user_id)
            except Exception:
                _safe_rollback(db)
                plan = "free"

            is_paid = (plan == "paid")

            try:
                used_24h = billing_repo.count_queries_last_24h(db, user_id=user_id)
            except Exception:
                _safe_rollback(db)
                used_24h = 10**9

            limit_24h = daily_limit_for_user(is_paid=is_paid)
            if used_24h >= limit_24h:
                raise HTTPException(status_code=429, detail="Daily query limit reached. Create an account or upgrade to continue.")

            require_credits = (not is_paid) and (used_24h >= settings.free_daily_limit)
            if require_credits:
                try:
                    ok = billing_repo.spend_credits(db, user_id=user_id, amount=settings.credits_per_query, reason="query")
                except Exception:
                    _safe_rollback(db)
                    ok = False
                if not ok:
                    raise HTTPException(status_code=402, detail="Out of credits. Purchase more to continue.")

            _insert_message(db, session_id=req.session_id, role="user", content=req.query)

            result = await run_pipeline(
                query=req.query,
                session_id=req.session_id,
                user_id=user_id,
                compare=bool(getattr(req, "compare", False)),
                max_tokens=max_tokens_for_tier(is_paid=is_paid),
                conversation=conversation,
                state=state,
            )

            _insert_message(db, session_id=req.session_id, role="assistant", content=result.get("answer", ""))

        # -------------------------
        # Phase 2B: Update state deterministically
        # -------------------------
        try:
            row = db.execute(
                text("select count(*) from messages where session_id=:sid"),
                {"sid": req.session_id},
            ).fetchone()
            turn_count = int(row[0]) if row else 0

            if _should_update_state(turn_count):
                recent = memory_repo.get_recent_messages(db, req.session_id, limit=24)
                prev = memory_repo.get_state(db, req.session_id)
                new_state = _extract_state_from_recent(recent, prev_state=prev)
                memory_repo.upsert_state(db, req.session_id, new_state)
                _safe_commit(db)
        except Exception:
            _safe_rollback(db)

        return AskResponse(**result)

    except HTTPException:
        raise
    except SQLAlchemyError:
        _safe_rollback(db)
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        _safe_rollback(db)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if db:
            db.close()


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/diagnostics/providers")
async def diagnostics_providers():
    return {
        "OPENAI": {
            "api_key_set": bool(settings.openai_api_key),
            "router_model": settings.openai_router_model,
            "ranker_model": settings.openai_ranker_model,
            "answer_model": settings.openai_answer_model,
        },
        "PERPLEXITY": {
            "api_key_set": bool(settings.perplexity_api_key),
            "base_url": settings.perplexity_base_url,
            "model": settings.perplexity_model,
        },
        "GROK": {
            "api_key_set": bool(settings.grok_api_key),
            "base_url": settings.grok_base_url,
            "model": settings.grok_model,
        },
        "CLAUDE": {
            "api_key_set": bool(settings.anthropic_api_key),
            "base_url": settings.anthropic_base_url,
            "model": settings.anthropic_model,
        },
        "GEMINI": {
            "api_key_set": bool(settings.gemini_api_key),
            "base_url": settings.gemini_base_url,
            "model": settings.gemini_model,
        },
        "DATABASE": {"database_url_set": bool(settings.database_url)},
    }


@app.get("/diagnostics/ip")
async def diagnostics_ip(request: Request):
    return {
        "client_host": request.client.host if request.client else None,
        "cf_connecting_ip": request.headers.get("cf-connecting-ip"),
        "true_client_ip": request.headers.get("true-client-ip"),
        "x_real_ip": request.headers.get("x-real-ip"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "user_agent": request.headers.get("user-agent"),
    }
