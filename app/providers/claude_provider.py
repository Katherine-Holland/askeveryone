import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError


class ClaudeProvider(BaseProvider):
    name = "CLAUDE"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.anthropic_api_key:
            raise ProviderError("ANTHROPIC_API_KEY not set")

        base_url = (settings.anthropic_base_url or "https://api.anthropic.com").rstrip("/")
        url = f"{base_url}/v1/messages"

        today = meta.get("today_utc")
        system_prompt = (
            "You are Seekle (Ask Everyone). Answer clearly, thoroughly, and safely.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources."
        )

        # ✅ Max tokens comes from orchestrator meta, with a safe default fallback
        max_tokens = int(meta.get("max_tokens") or 800)
        # Avoid silly values that can break requests
        if max_tokens < 64:
            max_tokens = 64
        if max_tokens > 4000:
            max_tokens = 4000

        payload = {
            "model": settings.anthropic_model,
            "max_tokens": max_tokens,   # ✅ UPDATED
            "temperature": 0.4,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": query}]}
            ],
        }

        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()

            parts = []
            for block in data.get("content", []):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))

            return "\n".join([p for p in parts if p]).strip() or ""

        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text[:300]
            except Exception:
                pass
            raise ProviderError(f"Claude HTTP {e.response.status_code}: {body}") from e

        except Exception as e:
            raise ProviderError(f"Claude error: {type(e).__name__}") from e
