# app/providers/gemini_provider.py
from __future__ import annotations

import httpx
from typing import Dict, Any, List, Tuple

from app.config import settings
from .base import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    name = "GEMINI"

    def _build_gemini_contents(self, meta: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """
        Gemini generateContent expects:
          contents: [{ role: "user"|"model", parts: [{text:"..."}] }, ...]
        We'll map:
          - role=user -> "user"
          - role=assistant -> "model"
        We'll also ignore "system" (Gemini v1beta generateContent doesn't have a true system role),
        so system instructions are added via a leading user message.
        """
        raw_msgs = meta.get("messages")
        contents: List[Dict[str, Any]] = []

        if isinstance(raw_msgs, list) and raw_msgs:
            for m in raw_msgs:
                if not isinstance(m, dict):
                    continue
                role = (m.get("role") or "").strip()
                content = (m.get("content") or "").strip()
                if not content:
                    continue

                if role == "system":
                    continue

                if role == "user":
                    contents.append({"role": "user", "parts": [{"text": content}]})
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [{"text": content}]})
                else:
                    continue

        if contents:
            return contents

        # Fallback: single-turn
        return [{"role": "user", "parts": [{"text": query}]}]

    def _clamp_max_tokens(self, meta: Dict[str, Any]) -> int:
        max_tokens = int(meta.get("max_tokens") or 800)
        if max_tokens < 64:
            max_tokens = 64
        if max_tokens > 4096:
            max_tokens = 4096
        return max_tokens

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
            "For follow-up questions, infer missing context from the conversation.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources."
        )

        max_tokens = self._clamp_max_tokens(meta)

        # Build conversation contents from meta["messages"], then prefix the system text as the first user turn.
        contents = self._build_gemini_contents(meta=meta, query=query)

        # Ensure the system instructions are always present (Gemini doesn't have a system role here)
        # Put instructions first as a user message to steer the model.
        contents = [{"role": "user", "parts": [{"text": system_text}]}] + contents

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": max_tokens,
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

            status = e.response.status_code
            if status == 429:
                raise ProviderError("Gemini quota/rate limit hit (429).") from e

            raise ProviderError(f"Gemini HTTP {status}: {body}") from e

        except ProviderError:
            raise

        except Exception as e:
            raise ProviderError(f"Gemini error: {type(e).__name__}") from e
