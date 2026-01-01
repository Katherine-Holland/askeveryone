from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

import httpx

from app.schemas import AskRequest, AskResponse
from app.orchestrator import run_pipeline
from app.config import settings
from app.db.session import init_engine
from app.db.models import Base

app = FastAPI(title="AskEveryone (SQL AI)")

def init_db():
    engine = init_engine()
    if engine is None:
        return
    Base.metadata.create_all(bind=engine)



@app.on_event("startup")
async def startup_event():
    # Create tables on boot (Neon)
    init_db()


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
        "endpoints": ["/health", "/ask", "/diagnostics/providers"]
    }


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    try:
        result = await run_pipeline(query=req.query, session_id=req.session_id)
        return AskResponse(**result)
    except Exception as e:
        # Temporary: show the error message for debugging.
        # Later, replace with a generic message + internal logging.
        raise HTTPException(status_code=500, detail=str(e))


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
        }
    }
