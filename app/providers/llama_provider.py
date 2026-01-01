import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError
import os

class LlamaProvider(BaseProvider):
    name = "LLAMA"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        llama_key = getattr(settings, "llama_api_key", "") or os.getenv("LLAMA_API_KEY", "")
        llama_base = getattr(settings, "llama_base_url", "") or os.getenv("LLAMA_BASE_URL", "")
        llama_model = os.getenv("LLAMA_MODEL", "")

        if not llama_key or not llama_base or not llama_model:
            raise ProviderError("LLAMA_API_KEY / LLAMA_BASE_URL / LLAMA_MODEL not set")

        payload = {
            "model": llama_model,
            "messages": [
                {"role": "system", "content": "You are SQL AI. Answer the user clearly and helpfully."},
                {"role": "user", "content": query},
            ],
            "temperature": 0.4,
        }

        url = llama_base.rstrip("/") + "/chat/completions"

        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                url,
                headers={"Authorization": f"Bearer {llama_key}"},
                json=payload,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
