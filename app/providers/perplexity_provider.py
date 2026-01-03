import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError


class PerplexityProvider(BaseProvider):
    name = "PERPLEXITY"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.perplexity_api_key:
            raise ProviderError("PERPLEXITY_API_KEY not set")

        base_url = (settings.perplexity_base_url or "https://api.perplexity.ai").rstrip("/")
        url = f"{base_url}/chat/completions"

        today = meta.get("today_utc")
        want_citations = bool(meta.get("features", {}).get("citations", False)) or (
            intent == "WEB_RESEARCH_CITATIONS"
        )

        system_prompt = (
            "You are Seekle (Ask Everyone). Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources.\n"
            + ("Include citations/links when helpful." if want_citations else "")
        )

        payload = {
            "model": settings.perplexity_model or "sonar-pro",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "temperature": 0.3,
        }

        headers = {
            "Authorization": f"Bearer {settings.perplexity_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()

            # OpenAI-style
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body = ""
            try:
                body = e.response.text[:400]
            except Exception:
                pass

            if status == 429:
                raise ProviderError("Perplexity quota/rate limit hit (429).") from e

            raise ProviderError(f"Perplexity HTTP {status}: {body}") from e

        except Exception as e:
            raise ProviderError(f"Perplexity error: {type(e).__name__}") from e
