from fastapi import FastAPI
from app.schemas import AskRequest, AskResponse
from app.orchestrator import run_pipeline
from app.config import settings
from app.db.session import _engine
from app.db.models import Base

app = FastAPI(title="AskEveryone (SQL AI)")

def init_db():
    if _engine is None:
        return
    Base.metadata.create_all(bind=_engine)

@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    result = await run_pipeline(query=req.query, session_id=req.session_id)
    return AskResponse(**result)

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

