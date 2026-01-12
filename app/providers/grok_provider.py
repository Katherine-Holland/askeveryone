# app/providers/grok_provider.py
from __future__ import annotations

import httpx
from typing import Dict, Any, List

from app.config import settings
from .base import BaseProvider, ProviderError


class GrokProvider(BaseProvider):
    name = "GROK"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.grok_api_key:
            raise ProviderError("GROK_API_KEY not set")

        base_url = (settings.grok_base_url or "https://api.x.ai").rstrip("/")
        url = f"{base_url}/v1/chat/completions"

        today = meta.get("today_utc", "unknown")
        system_prompt = (
            "You are Seekle (Ask Everyone). Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "For follow-up questions, infer missing context from the conversation.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources."
        )

        # ✅ Max tokens from orchestrator meta
        max_tokens = int(meta.get("max_tokens") or 800)
        if max_tokens < 64:
            max_tokens = 64
        if max_tokens > 4000:
            max_tokens = 4000

        # ✅ Step D: use conversation context if provided
        msgs: List[Dict[str, str]] = []
        raw_msgs = meta.get("messages")

        if isinstance(raw_msgs, list) and raw_msgs:
            for m in raw_msgs:
                if not isinstance(m, dict):
                    continue
                role = (m.get("role") or "").strip()
                content = (m.get("content") or "").strip()
                if role in ("system", "user", "assistant") and content:
                    msgs.append({"role": role, "content": content})

        if msgs:
            # Prepend our authoritative system message and drop other system messages
            messages = [{"role": "system", "content": system_prompt}] + [
                m for m in msgs if m.get("role") != "system"
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ]

        payload: Dict[str, Any] = {
            "model": settings.grok_model or "grok-beta",
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {settings.grok_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise ProviderError("Grok request timed out")
        except Exception as e:
            raise ProviderError(f"Grok request failed: {type(e).__name__}")

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text[:600]
            except Exception:
                pass

            status = e.response.status_code
            if status == 429:
                raise ProviderError("Grok quota/rate limit hit (429).") from e

            raise ProviderError(f"Grok HTTP {status}: {body}") from e

        data = r.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            raise ProviderError("Grok response parsing error")
