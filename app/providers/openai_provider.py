# app/providers/openai_provider.py
from __future__ import annotations

import httpx
from typing import Dict, Any, List

from app.config import settings
from .base import BaseProvider, ProviderError


class OpenAIProvider(BaseProvider):
    name = "OPENAI"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY not set")

        # Authoritative date (from orchestrator)
        today = meta.get("today_utc", "unknown")

        # Base system prompt (always enforce)
        system_prompt = (
            "You are SEEKLE. Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. "
            "If the user asks for today's date or the current day, use this value. "
            "If you are unsure, say you are not sure rather than guessing.\n"
            "Important: For follow-up questions, infer missing context from the conversation."
        )

        # ✅ Max tokens comes from orchestrator meta, with safe bounds
        max_tokens = int(meta.get("max_tokens") or 800)
        if max_tokens < 64:
            max_tokens = 64
        if max_tokens > 4000:
            max_tokens = 4000

        # ✅ Step D: use normalized conversation if present
        # meta["messages"] should be a list[{"role": "...", "content": "..."}]
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
            # Ensure our system prompt is applied even if orchestrator already added system messages.
            # We *prepend* one authoritative system message.
            messages = [{"role": "system", "content": system_prompt}] + [
                m for m in msgs if m.get("role") != "system"
            ]
        else:
            # Fallback (old behavior)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ]

        payload = {
            "model": settings.openai_answer_model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException:
            raise ProviderError("OpenAI request timed out")
        except Exception as e:
            raise ProviderError(f"OpenAI request failed: {type(e).__name__}")

        if r.status_code >= 400:
            # keep this short to avoid logging huge payloads
            raise ProviderError(f"{r.status_code} {r.text[:600]}")

        data = r.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            raise ProviderError("OpenAI response parsing error")
