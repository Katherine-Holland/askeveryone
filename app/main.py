from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import httpx
import uuid

from sqlalchemy import text

from app.api.metrics import router as metrics_router
from app.schemas import AskRequest, AskResponse
from app.orchestrator import run_pipeline
from app.config import settings
from app.db.session import init_engine, get_session
from app.api.diagnostics import router as diagnostics_router
from app.api.test_provider import router as test_provider_router
from app.api.billing import router as billing_router
app.include_router(billing_router)

# NEW: limits + billing
from app.limits import daily_limit_for_user, max_tokens_for_tier
from app.db import billing_repo

# Use ONE shared Base across all models
from app.db.base import Base

# IMPORTANT: import model modules so Base.metadata knows about all tables
import app.db.models          # queries/provider_calls
import app.db.models_auth     # users/chat_sessions/messages/magic_links (+ billing models if you add them later)
import app.db.models_billing

# Mount API routers
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router

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


# ---------- Diagnostics ----------
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
        ],
    }


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


# ---------- Core endpoint ----------
@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    db = None
    try:
        db = get_session()

        # 1) Ensure session exists (even if /chat/start not called)
        if db and req.session_id:
            db.execute(
                text(
                    "insert into chat_sessions (session_id, is_anonymous) "
                    "values (:sid, true) on conflict (session_id) do nothing"
                ),
                {"sid": req.session_id},
            )
            db.commit()

        # 2) Resolve user_id from session (claimed sessions have user_id)
        user_id = None
        is_paid = False

        if db and req.session_id:
            row = db.execute(
                text("select user_id from chat_sessions where session_id=:sid"),
                {"sid": req.session_id},
            ).fetchone()
            user_id = row[0] if row and row[0] else None

        # 3) Enforce login for “5 free queries/day”
        # (Anonymous can still chat if you want, but you asked: logged-in required for free 5)
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Please log in with email to use the free daily queries.",
            )

        # 4) Ensure billing rows exist + determine plan
        billing_repo.ensure_wallet_and_plan(db, user_id)
        plan = billing_repo.get_user_plan(db, user_id)
        is_paid = plan == "paid"

        # 5) Daily cap (paid still capped until we trust patterns)
        used_24h = billing_repo.count_queries_last_24h(db, user_id=user_id)
        limit_24h = daily_limit_for_user(is_paid=is_paid)

        if used_24h >= limit_24h:
            raise HTTPException(
                status_code=429,
                detail=f"Daily query limit reached ({limit_24h}/24h). Try again tomorrow.",
            )

        # 6) Credits logic (free tier: first N/day free; then credits required)
        require_credits = False
        credits_to_spend = settings.credits_per_query

        if not is_paid and used_24h >= settings.free_daily_limit:
            require_credits = True

        if require_credits:
            ok = billing_repo.spend_credits(
                db,
                user_id=user_id,
                amount=credits_to_spend,
                reason="query",
            )
            if not ok:
                raise HTTPException(
                    status_code=402,
                    detail="Out of credits. Please purchase more to continue.",
                )

        # 7) Log user message
        if db and req.session_id:
            db.execute(
                text(
                    "insert into messages (message_id, session_id, role, content) "
                    "values (:mid, :sid, :role, :content)"
                ),
                {
                    "mid": uuid.uuid4(),
                    "sid": req.session_id,
                    "role": "user",
                    "content": req.query,
                },
            )
            db.commit()

        # 8) Run pipeline with token cap and optional compare
        result = await run_pipeline(
            query=req.query,
            session_id=req.session_id,
            user_id=user_id,
            compare=bool(getattr(req, "compare", False)),
            max_tokens=max_tokens_for_tier(is_paid=is_paid),
        )

        # 9) Log assistant message
        if db and req.session_id:
            db.execute(
                text(
                    "insert into messages (message_id, session_id, role, content) "
                    "values (:mid, :sid, :role, :content)"
                ),
                {
                    "mid": uuid.uuid4(),
                    "sid": req.session_id,
                    "role": "assistant",
                    "content": result.get("answer", ""),
                },
            )
            db.commit()

        return AskResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
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
