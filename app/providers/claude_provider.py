import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError

class ClaudeProvider(BaseProvider):
    name = "CLAUDE"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.anthropic_api_key:
            raise ProviderError("ANTHROPIC_API_KEY not set")

        url = settings.anthropic_base_url.rstrip("/") + "/v1/messages"

        # Anthropic uses "messages" with "content" blocks
        payload = {
            "model": settings.anthropic_model,
            "max_tokens": 800,
            "temperature": 0.4,
            "system": "You are SQL AI. Answer clearly, thoroughly, and safely.",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": query}]}
            ],
        }

        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

            # content is list of blocks; return concatenated text blocks
            parts = []
            for block in data.get("content", []):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "\n".join([p for p in parts if p]).strip() or ""
