# app/providers/gemini_provider.py
from __future__ import annotations

import httpx
from typing import Dict, Any, List

from app.config import settings
from .base import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    name = "GEMINI"

    def _clamp_max_tokens(self, meta: Dict[str, Any]) -> int:
        max_tokens = int(meta.get("max_tokens") or 800)
        if max_tokens < 64:
            max_tokens = 64
        if max_tokens > 4096:
            max_tokens = 4096
        return max_tokens

    def _extract_orchestrator_system(self, meta: Dict[str, Any]) -> str:
        """
        Pulls system messages from meta["messages"] (Memory + Conversation State)
        so Gemini actually gets the session context.
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

        # Deduplicate exact duplicates (cheap)
        deduped: List[str] = []
        seen = set()
        for s in sys_parts:
            k = s.strip()
            if k and k not in seen:
                deduped.append(k)
                seen.add(k)

        return "\n\n".join(deduped).strip()

    def _build_gemini_contents(self, meta: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """
        Gemini generateContent expects:
          contents: [{ role: "user"|"model", parts: [{text:"..."}] }, ...]

        We map:
          - role=user -> "user"
          - role=assistant -> "model"
          - role=system -> ignored here (handled via systemInstruction or a prefixed user message)

        Important: orchestrator meta["messages"] already includes the current user turn.
        We'll only append query if we end up with no usable history.
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

                if role == "user":
                    contents.append({"role": "user", "parts": [{"text": content}]})
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [{"text": content}]})
                else:
                    # skip system/unknown here
                    continue

        if contents:
            return contents

        # Fallback: single-turn
        return [{"role": "user", "parts": [{"text": query}]}]

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY not set")

        base_url = (settings.gemini_base_url or "https://generativelanguage.googleapis.com").rstrip("/")
        model = settings.gemini_model or "gemini-1.5-pro"

        # Gemini REST: POST .../v1beta/models/{model}:generateContent?key=...
        url = f"{base_url}/v1beta/models/{model}:generateContent"
        params = {"key": settings.gemini_api_key}

        today = meta.get("today_utc", "unknown")

        base_system_text = (
            "You are Seekle (Ask Everyone). Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "Important: For follow-up questions, infer missing context from the conversation and Conversation State.\n"
            "If unsure about a time-sensitive fact, say you're not sure and suggest checking sources."
        )

        # ✅ Pull Memory / Conversation State from orchestrator system messages
        orchestrator_system = self._extract_orchestrator_system(meta)
        if orchestrator_system:
            system_text = (
                base_system_text
                + "\n\n---\nConversation State (from memory + prior turns):\n"
                + orchestrator_system
            )
        else:
            system_text = base_system_text

        max_tokens = self._clamp_max_tokens(meta)

        # Build conversation contents from meta["messages"] (user/model turns)
        contents = self._build_gemini_contents(meta=meta, query=query)

        # ✅ Preferred: use systemInstruction if supported by your endpoint/model.
        # If you ever see 400 "Unknown name 'systemInstruction'", switch to the fallback below.
        payload: Dict[str, Any] = {
            "systemInstruction": {
                "parts": [{"text": system_text}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(url, params=params, json=payload)

            # If the API rejects systemInstruction, fall back safely.
            if r.status_code == 400 and "systemInstruction" in (r.text or ""):
                fallback_payload = {
                    "contents": [{"role": "user", "parts": [{"text": system_text}]}] + contents,
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": max_tokens,
                    },
                }
                async with httpx.AsyncClient(timeout=45.0) as client:
                    r = await client.post(url, params=params, json=fallback_payload)

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
                body = e.response.text[:600]
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
