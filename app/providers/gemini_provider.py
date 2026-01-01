import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError

class GeminiProvider(BaseProvider):
    name = "GEMINI"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY not set")

        # Google Generative Language API: models/{model}:generateContent?key=...
        base = settings.gemini_base_url.rstrip("/")
        url = f"{base}/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": query}]}
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 800,
            },
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

            # candidates[0].content.parts[].text
            candidates = data.get("candidates", [])
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
            return "\n".join([t for t in texts if t]).strip() or ""
