import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    name = "GEMINI"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY not set")

        base_url = (settings.gemini_base_url or "https://generativelanguage.googleapis.com").rstrip("/")
        model = settings.gemini_model or "gemini-1.5-pro"

        # Gemini REST: POST .../v1beta/models/{model}:generateContent?key=...
        url = f"{base_url}/v1beta/models/{model}:generateContent"
        params = {"key": settings.gemini_api_key}

        today = meta.get("today_utc", "unknown")
        system_text = (
            "You are Seekle (Ask Everyone). Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources."
        )

        # ✅ Max tokens from orchestrator meta (Gemini uses maxOutputTokens)
        max_tokens = int(meta.get("max_tokens") or 800)
        if max_tokens < 64:
            max_tokens = 64
        # Gemini max varies by model; 4096 is a safe-ish upper bound for output caps.
        if max_tokens > 4096:
            max_tokens = 4096

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_text}\n\nUser: {query}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": max_tokens,  # ✅ UPDATED
            },
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(url, params=params, json=payload)
                r.raise_for_status()
                data = r.json()

            candidates = data.get("candidates") or []
            if not candidates:
                raise ProviderError(f"Gemini empty candidates: {str(data)[:200]}")

            content = (candidates[0].get("content") or {})
            parts = content.get("parts") or []
            texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
            answer = "".join(texts).strip()

            if not answer:
                raise ProviderError(f"Gemini returned no text: {str(data)[:200]}")

            return answer

        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text[:400]
            except Exception:
                pass
            raise ProviderError(f"Gemini HTTP {e.response.status_code}: {body}") from e

        except ProviderError:
            raise

        except Exception as e:
            raise ProviderError(f"Gemini error: {type(e).__name__}") from e
