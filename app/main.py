# app/main.py
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
import httpx
import uuid

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.schemas import AskRequest, AskResponse
from app.orchestrator import run_pipeline
from app.config import settings
from app.db.session import init_engine, get_session

# limits + billing
from app.limits import daily_limit_for_user, max_tokens_for_tier
from app.db import billing_repo

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
    """
    Best-effort message logging.
    If it fails, rollback so we don't poison the session for later work.
    """
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
        ],
    }


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request):
    """
    Policy:
    - Anonymous: 1 free/day per IP+UA hash AND global anonymous pool 200/day.
    - Logged-in: 5 free/day, then credits/subscription, plus daily hard cap.
    """
    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        if not req.session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        # Clear any poisoned transaction state from prior exceptions
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

        # Resolve user_id from session
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

        # -------------------------
        # Anonymous gating (no Turnstile)
        # -------------------------
        if user_id is None:
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent")
            key_hash = build_anon_key(ip=ip, user_agent=ua)

            # 1) Global pool cap
            try:
                used_global = anon_global_used_today(db)
            except Exception:
                _safe_rollback(db)
                used_global = 10**9  # fail-closed

            if used_global >= int(getattr(settings, "anon_global_pool_per_day", 200)):
                raise HTTPException(
                    status_code=402,
                    detail="Free access is busy right now. Create a free account to continue and save your conversation.",
                )

            # 2) Per-key 1/day
            try:
                used_key = anon_allowance_used_today(db, key_hash)
            except Exception:
                _safe_rollback(db)
                used_key = 10**9  # fail-closed

            if used_key >= int(getattr(settings, "anon_free_per_24h", 1)):
                raise HTTPException(
                    status_code=402,
                    detail="Create a free account to save your conversation and continue searching.",
                )

            # 3) Record usage BEFORE calling providers (fail-closed)
            try:
                record_anon_use_today(db, key_hash)
                record_anon_global_use_today(db)
                _safe_commit(db)
            except Exception:
                _safe_rollback(db)
                raise HTTPException(
                    status_code=429,
                    detail="Temporary protection triggered. Please create a free account to continue.",
                )

            # Best-effort logging
            _insert_message(db, session_id=req.session_id, role="user", content=req.query)

            # Run pipeline as free tier
            result = await run_pipeline(
                query=req.query,
                session_id=req.session_id,
                user_id=None,
                compare=bool(getattr(req, "compare", False)),
                max_tokens=max_tokens_for_tier(is_paid=False),
            )

            _insert_message(db, session_id=req.session_id, role="assistant", content=result.get("answer", ""))
            return AskResponse(**result)

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

        # Hard daily cap (anti-abuse)
        try:
            used_24h = billing_repo.count_queries_last_24h(db, user_id=user_id)
        except Exception:
            _safe_rollback(db)
            used_24h = 10**9  # fail-closed

        limit_24h = daily_limit_for_user(is_paid=is_paid)
        if used_24h >= limit_24h:
            raise HTTPException(
                status_code=429,
                detail=f"Daily query limit reached. Create an account or upgrade to continue.",
            )

        # Credits logic: free users get first N/day free, then spend credits
        require_credits = (not is_paid) and (used_24h >= settings.free_daily_limit)
        if require_credits:
            try:
                ok = billing_repo.spend_credits(
                    db,
                    user_id=user_id,
                    amount=settings.credits_per_query,
                    reason="query",
                )
            except Exception:
                _safe_rollback(db)
                ok = False

            if not ok:
                raise HTTPException(
                    status_code=402,
                    detail="Out of credits. Purchase more to continue.",
                )

        _insert_message(db, session_id=req.session_id, role="user", content=req.query)

        result = await run_pipeline(
            query=req.query,
            session_id=req.session_id,
            user_id=user_id,
            compare=bool(getattr(req, "compare", False)),
            max_tokens=max_tokens_for_tier(is_paid=is_paid),
        )

        _insert_message(db, session_id=req.session_id, role="assistant", content=result.get("answer", ""))
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
        "LLAMA": {
            "api_key_set": bool(settings.llama_api_key),
            "base_url": settings.llama_base_url,
            "model": settings.llama_model,
        },
        "HUGGINGFACE": {
            "api_key_set": bool(settings.huggingface_api_key),
            "base_url": settings.huggingface_base_url,
            "model": settings.huggingface_model,
        },
        "DATABASE": {"database_url_set": bool(settings.database_url)},
    }
