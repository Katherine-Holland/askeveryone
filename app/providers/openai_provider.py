import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError


class OpenAIProvider(BaseProvider):
    name = "OPENAI"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY not set")

        # Inject authoritative date to prevent hallucination
        today = meta.get("today_utc", "unknown")

        system_prompt = (
            "You are SEEKLE. Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. "
            "If the user asks for today's date or the current day, use this value. "
            "If you are unsure, say you are not sure rather than guessing."
        )

        payload = {
            "model": settings.openai_answer_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "temperature": 0.4,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            # Raise with body if something ever goes wrong again
            if r.status_code >= 400:
                raise ProviderError(f"{r.status_code} {r.text}")

            return r.json()["choices"][0]["message"]["content"].strip()
