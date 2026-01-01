import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError

class OpenAIProvider(BaseProvider):
    name = "OPENAI"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY not set")

        payload = {
            "model": settings.openai_answer_model,
            "messages": [
                {"role": "system", "content": "You are SQL AI. Answer the user clearly and helpfully."},
                {"role": "user", "content": query},
            ],
            "temperature": 0.4,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
