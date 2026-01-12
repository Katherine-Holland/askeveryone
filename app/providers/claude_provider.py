# app/providers/claude_provider.py
from __future__ import annotations

import httpx
from typing import Dict, Any, List

from app.config import settings
from .base import BaseProvider, ProviderError


class ClaudeProvider(BaseProvider):
    name = "CLAUDE"

    def _extract_system_context(self, meta: Dict[str, Any]) -> str:
        """
        Claude messages do NOT support role='system', so we must move any orchestrator
        system messages (Memory / Conversation State) into the top-level 'system' prompt.
        """
        raw_msgs = meta.get("messages")
        if not isinstance(raw_msgs, list) or not raw_msgs:
            return ""

        sys_parts: List[str] = []
        for m in raw_msgs:
            if not isinstance(m, dict):
                continue
            role = (m.get("role") or "").strip()
            content = (m.get("content") or "").strip()
            if role == "system" and content:
                sys_parts.append(content)

        # Deduplicate exact repeats (cheap)
        deduped: List[str] = []
        seen = set()
        for s in sys_parts:
            key = s.strip()
            if key and key not in seen:
                deduped.append(key)
                seen.add(key)

        return "\n\n".join(deduped).strip()

    def _build_claude_messages(self, meta: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """
        Anthropic expects:
          messages: [{ role: "user"|"assistant", content: [{type:"text", text:"..."}] }, ...]
        We'll use meta["messages"] if present; otherwise fall back to a single user turn.
        """
        raw_msgs = meta.get("messages")
        out: List[Dict[str, Any]] = []

        if isinstance(raw_msgs, list) and raw_msgs:
            for m in raw_msgs:
                if not isinstance(m, dict):
                    continue
                role = (m.get("role") or "").strip()
                content = (m.get("content") or "").strip()
                if not content:
                    continue

                # Claude API messages only allow user|assistant
                if role not in ("user", "assistant"):
                    continue

                out.append({"role": role, "content": [{"type": "text", "text": content}]})

        if out:
            return out

        # Fallback: single-turn
        return [{"role": "user", "content": [{"type": "text", "text": query}]}]

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.anthropic_api_key:
            raise ProviderError("ANTHROPIC_API_KEY not set")

        base_url = (settings.anthropic_base_url or "https://api.anthropic.com").rstrip("/")
        url = f"{base_url}/v1/messages"

        today = meta.get("today_utc", "unknown")

        # Provider-level system prompt (always enforce)
        base_system_prompt = (
            "You are Seekle (Ask Everyone). Answer clearly, thoroughly, and safely.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "Important: For follow-up questions, infer missing context from the conversation and Conversation State.\n"
            "Do not ask unnecessary clarification questions if the context is already present.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources."
        )

        # ✅ Pull orchestrator system messages (Memory / State) into Claude's system prompt
        orchestrator_system = self._extract_system_context(meta)
        if orchestrator_system:
            system_prompt = (
                base_system_prompt
                + "\n\n---\nConversation State (from memory + prior turns):\n"
                + orchestrator_system
            )
        else:
            system_prompt = base_system_prompt

        # Max tokens from orchestrator meta
        max_tokens = int(meta.get("max_tokens") or 800)
        if max_tokens < 64:
            max_tokens = 64
        if max_tokens > 4000:
            max_tokens = 4000

        messages = self._build_claude_messages(meta=meta, query=query)

        payload: Dict[str, Any] = {
            "model": settings.anthropic_model,
            "max_tokens": max_tokens,
            "temperature": 0.4,
            "system": system_prompt,
            "messages": messages,
        }

        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise ProviderError("Claude request timed out")
        except Exception as e:
            raise ProviderError(f"Claude request failed: {type(e).__name__}") from e

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
                raise ProviderError("Claude quota/rate limit hit (429).") from e

            raise ProviderError(f"Claude HTTP {status}: {body}") from e

        data = r.json()

        # Claude returns: { content: [ {type:"text", text:"..."}, ... ] }
        parts: List[str] = []
        try:
            for block in data.get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    t = (block.get("text") or "").strip()
                    if t:
                        parts.append(t)
        except Exception as e:
            raise ProviderError("Claude response parsing error") from e

        return "\n".join(parts).strip() or ""
