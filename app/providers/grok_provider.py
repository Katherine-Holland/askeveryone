import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError

class GrokProvider(BaseProvider):
    name = "GROK"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.grok_api_key:
            raise ProviderError("GROK_API_KEY not set")

        # Many xAI endpoints are OpenAI-compatible; configurable base_url.
        url = settings.grok_base_url.rstrip("/") + "/v1/chat/completions"

        payload = {
            "model": settings.grok_model,
            "messages": [
                {"role": "system", "content": "Answer with emphasis on recent information when asked for latest/current updates."},
                {"role": "user", "content": query},
            ],
            "temperature": 0.3,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.grok_api_key}"},
                json=payload,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
