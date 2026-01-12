# app/providers/openai_provider.py
from __future__ import annotations

import httpx
from typing import Dict, Any, List

from app.config import settings
from .base import BaseProvider, ProviderError


class OpenAIProvider(BaseProvider):
    name = "OPENAI"

    def _extract_orchestrator_system(self, meta: Dict[str, Any]) -> str:
        raw = meta.get("messages")
        if not isinstance(raw, list):
            return ""

        parts: List[str] = []
        for m in raw:
            if not isinstance(m, dict):
                continue
            if (m.get("role") or "").strip() != "system":
                continue
            c = (m.get("content") or "").strip()
            if c:
                parts.append(c)

        # dedupe, preserve order
        out: List[str] = []
        seen = set()
        for p in parts:
            if p not in seen:
                out.append(p)
                seen.add(p)

        return "\n\n".join(out).strip()

    def _build_non_system_messages(self, meta: Dict[str, Any], query: str) -> List[Dict[str, str]]:
        raw = meta.get("messages")
        msgs: List[Dict[str, str]] = []

        if isinstance(raw, list) and raw:
            for m in raw:
                if not isinstance(m, dict):
                    continue
                role = (m.get("role") or "").strip()
                content = (m.get("content") or "").strip()
                if not content:
                    continue
                if role in ("user", "assistant"):
                    msgs.append({"role": role, "content": content})

        if msgs:
            return msgs

        return [{"role": "user", "content": query.strip()}]

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY not set")

        today = meta.get("today_utc", "unknown")

        system_prompt = (
            "You are SEEKLE. Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. "
            "If the user asks for today's date or the current day, use this value. "
            "If you are unsure, say you are not sure rather than guessing.\n"
            "For follow-up questions, infer missing context from the conversation.\n"
            "Do not ask unnecessary clarification questions if the context is already present.\n"
            "If the user changes topic, follow the new topic.\n"
        )

        orch_system = self._extract_orchestrator_system(meta)
        if orch_system:
            system_prompt += "\n---\nConversation State:\n" + orch_system

        max_tokens = int(meta.get("max_tokens") or 800)
        max_tokens = max(64, min(max_tokens, 4000))

        messages = [{"role": "system", "content": system_prompt}] + self._build_non_system_messages(meta, query)

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
            raise ProviderError(f"OpenAI request failed: {type(e).__name__}") from e

        if r.status_code >= 400:
            raise ProviderError(f"{r.status_code} {r.text[:600]}")

        try:
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise ProviderError("OpenAI response parsing error") from e
