from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timezone

from app.providers.base import ProviderError
from app.providers.grok_provider import GrokProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.perplexity_provider import PerplexityProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.llama_provider import LlamaProvider
from app.providers.huggingface_provider import HuggingFaceProvider


router = APIRouter(tags=["diagnostics"])

PROVIDERS = {
    "OPENAI": OpenAIProvider(),
    "GROK": GrokProvider(),
    "PERPLEXITY": PerplexityProvider(),
    "CLAUDE": ClaudeProvider(),
    "GEMINI": GeminiProvider(),
    "LLAMA": LlamaProvider(),
    "HUGGINGFACE": HuggingFaceProvider(),
}


@router.post("/diagnostics/test_provider")
async def test_provider(provider: str, query: str, intent: Optional[str] = "GENERAL_CHAT"):
    p = PROVIDERS.get(provider.upper())
    if not p:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    today_utc = datetime.now(timezone.utc).strftime("%B %d, %Y")
    meta = {"today_utc": today_utc, "features": {}, "plan": {}}

    try:
        answer = await p.ask(query=query, intent=intent or "GENERAL_CHAT", meta=meta)
        return {"ok": True, "provider": provider.upper(), "answer": answer[:2000]}
    except ProviderError as e:
        raise HTTPException(status_code=500, detail=str(e))
