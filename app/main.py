# app/main.py
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
import httpx
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.schemas import AskRequest, AskResponse
from app.orchestrator import run_pipeline
from app.config import settings
from app.db.session import init_engine, get_session
from app.api import shop

# limits + billing
from app.limits import daily_limit_for_user, max_tokens_for_tier
from app.db import billing_repo

# conversation + memory
from app.db import memory_repo
from app.memory_summarizer import build_transcript, summarize_with_openai

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
app.include_router(shop.router)


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


def _should_update_memory(turn_count: int) -> bool:
    n = int(getattr(settings, "memory_update_every_n_turns", 6))
    if n <= 0:
        return False
    return (turn_count % n) == 0


async def _maybe_update_memory(db, session_id: str) -> None:
    """
    Step 2D:
    - Pull a transcript window
    - Run strict memory summariser
    - Upsert memory (with digest if supported)
    Never raises.
    """
    try:
        # current turn count
        row = db.execute(
            text("select count(*) from messages where session_id=:sid"),
            {"sid": session_id},
        ).fetchone()
        turn_count = int(row[0]) if row else 0

        if not _should_update_memory(turn_count):
            return

        # fetch transcript window for summarisation
        msg_window = int(getattr(settings, "memory_summary_window", 40))
        recent = memory_repo.get_recent_messages_for_summary(db, session_id, limit=msg_window)

        transcript = build_transcript(recent, max_chars=9000)

        prev_summary, prev_digest = memory_repo.get_memory_and_digest(db, session_id)

        # If digest matches, skip (prevents re-summarising same content)
        # If no digest column exists, prev_digest will be "" so we won't skip.
        # The summariser returns digest for the transcript chunk.
        today_utc = datetime.now(timezone.utc).strftime("%B %d, %Y")

        new_summary, new_digest = await summarize_with_openai(
            previous_memory=prev_summary,
            transcript=transcript,
            today_utc=today_utc,
            timeout_s=45.0,
        )

        if prev_digest and new_digest and (prev_digest == new_digest):
            return

        max_chars = int(getattr(settings, "max_memory_chars", 1200))
        new_summary = (new_summary or "").strip()[:max_chars]

        if not new_summary:
            return

        # store digest if column exists; repo falls back if not
        memory_repo.upsert_memory(db, session_id, new_summary, digest=new_digest)
        _safe_commit(db)

    except Exception:
        _safe_rollback(db)
        return


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

        # Load conversation + memory (2C + 2D)
        history_limit = int(getattr(settings, "conversation_history_limit", 16))
        conversation = []
        memory = ""
        try:
            conversation = memory_repo.get_recent_messages(db, req.session_id, limit=history_limit)
            memory = memory_repo.get_memory(db, req.session_id)
        except Exception:
            _safe_rollback(db)
            conversation = []
            memory = ""

        # -------------------------
        # Anonymous gating
        # -------------------------
        if user_id is None:
            ip = _get_client_ip(request)
            ua = _norm_ua(request.headers.get("user-agent"))
            key_hash = build_anon_key(ip=ip, user_agent=ua)

            anon_global_cap = int(getattr(settings, "anon_global_pool_per_day", 300))
            anon_key_cap = int(getattr(settings, "anon_free_per_24h", 2))
            anon_session_cap = int(getattr(settings, "anon_session_free_per_day", 2))

            # 0) Per-session cap (UTC day)
            try:
                used_session_today = _anon_session_used_today(db, req.session_id)
            except Exception:
                _safe_rollback(db)
                used_session_today = 10**9

            if used_session_today >= anon_session_cap:
                raise HTTPException(
                    status_code=402,
                    detail="Create a free account to save your conversation and continue searching.",
                )

            # 1) Global pool cap
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

            # 2) Per-key cap
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

            # 3) Record usage BEFORE calling providers
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

            _insert_message(db, session_id=req.session_id, role="user", content=req.query)

            result = await run_pipeline(
                query=req.query,
                session_id=req.session_id,
                user_id=None,
                compare=bool(getattr(req, "compare", False)),
                max_tokens=max_tokens_for_tier(is_paid=False),
                conversation=conversation,
                memory=memory,
            )

            _insert_message(db, session_id=req.session_id, role="assistant", content=result.get("answer", ""))

            # Step 2D memory update (non-blocking / fail-open)
            await _maybe_update_memory(db, req.session_id)

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

        # Hard daily cap
        try:
            used_24h = billing_repo.count_queries_last_24h(db, user_id=user_id)
        except Exception:
            _safe_rollback(db)
            used_24h = 10**9

        limit_24h = daily_limit_for_user(is_paid=is_paid)
        if used_24h >= limit_24h:
            raise HTTPException(
                status_code=429,
                detail="Daily query limit reached. Create an account or upgrade to continue.",
            )

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
            conversation=conversation,
            memory=memory,
        )

        _insert_message(db, session_id=req.session_id, role="assistant", content=result.get("answer", ""))

        # Step 2D memory update
        await _maybe_update_memory(db, req.session_id)

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
