# app/providers/grok_provider.py
from __future__ import annotations

import httpx
from typing import Dict, Any, List

from app.config import settings
from .base import BaseProvider, ProviderError


class GrokProvider(BaseProvider):
    name = "GROK"

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
        if not settings.grok_api_key:
            raise ProviderError("GROK_API_KEY not set")

        base_url = (settings.grok_base_url or "https://api.x.ai").rstrip("/")
        url = f"{base_url}/v1/chat/completions"

        today = meta.get("today_utc", "unknown")
        system_prompt = (
            "You are Seekle (Ask Everyone). Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "For follow-up questions, infer missing context from the conversation.\n"
            "Do not ask unnecessary clarification questions if the context is already present.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources.\n"
        )

        orch_system = self._extract_orchestrator_system(meta)
        if orch_system:
            system_prompt += "\n---\nConversation State:\n" + orch_system

        max_tokens = int(meta.get("max_tokens") or 800)
        max_tokens = max(64, min(max_tokens, 4000))

        messages = [{"role": "system", "content": system_prompt}] + self._build_non_system_messages(meta, query)

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
            raise ProviderError(f"Grok request failed: {type(e).__name__}") from e

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body = ""
            try:
                body = e.response.text[:600]
            except Exception:
                pass
            if status == 429:
                raise ProviderError("Grok quota/rate limit hit (429).") from e
            raise ProviderError(f"Grok HTTP {status}: {body}") from e

        try:
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise ProviderError("Grok response parsing error") from e
