import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError


class GrokProvider(BaseProvider):
    name = "GROK"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.grok_api_key:
            raise ProviderError("GROK_API_KEY not set")

        base_url = (settings.grok_base_url or "https://api.x.ai").rstrip("/")
        url = f"{base_url}/v1/chat/completions"

        today = meta.get("today_utc")
        system_prompt = (
            "You are Seekle (Ask Everyone). Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources."
        )

        payload = {
            "model": settings.grok_model or "grok-beta",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "temperature": 0.4,
        }

        headers = {
            "Authorization": f"Bearer {settings.grok_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            # Include a short excerpt for debugging but don’t leak too much
            body = ""
            try:
                body = e.response.text[:300]
            except Exception:
                pass
            raise ProviderError(f"Grok HTTP {e.response.status_code}: {body}") from e
        except Exception as e:
            raise ProviderError(f"Grok error: {type(e).__name__}") from e
