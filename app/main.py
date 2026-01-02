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


# Use ONE shared Base across all models
from app.db.base import Base

# IMPORTANT: import model modules so Base.metadata knows about all tables
import app.db.models          # existing (queries/provider_calls etc.)
import app.db.models_auth     # new (users/chat_sessions/messages/magic_links)

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

        if db and req.session_id:
            # Ensure session exists even if /chat/start wasn't called
            db.execute(
                text(
                    "insert into chat_sessions (session_id, is_anonymous) "
                    "values (:sid, true) on conflict (session_id) do nothing"
                ),
                {"sid": req.session_id},
            )

            # Log user message
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

        # Run pipeline (router/provider/ranker + query/provider_call logging)
        result = await run_pipeline(query=req.query, session_id=req.session_id)

        # Log assistant message
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
        "DATABASE": {
            "database_url_set": bool(settings.database_url),
        },
    }
