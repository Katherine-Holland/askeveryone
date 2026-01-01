import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError

class PerplexityProvider(BaseProvider):
    name = "PERPLEXITY"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.perplexity_api_key:
            raise ProviderError("PERPLEXITY_API_KEY not set")

        url = settings.perplexity_base_url.rstrip("/") + "/chat/completions"

        payload = {
            "model": settings.perplexity_model,
            "messages": [
                {"role": "system", "content": "Answer accurately. If you use facts, prefer citing sources when available."},
                {"role": "user", "content": query},
            ],
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.perplexity_api_key}"},
                json=payload,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
