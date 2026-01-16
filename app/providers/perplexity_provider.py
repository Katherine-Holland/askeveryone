# app/providers/perplexity_provider.py
from __future__ import annotations

import httpx
import re
from typing import Dict, Any, List

from app.config import settings
from .base import BaseProvider, ProviderError


class PerplexityProvider(BaseProvider):
    name = "PERPLEXITY"

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

    def _normalize_search_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Perplexity Sonar returns web sources in `search_results`.
        Each element typically includes: title, url, date.
        """
        sr = data.get("search_results") or []
        if not isinstance(sr, list):
            return []

        out: List[Dict[str, str]] = []
        for r in sr:
            if not isinstance(r, dict):
                continue
            title = str(r.get("title") or "").strip()
            url = str(r.get("url") or "").strip()
            date = str(r.get("date") or "").strip()
            if not url and not title:
                continue
            out.append({"title": title, "url": url, "date": date})
        return out

    def _attach_citations(self, meta: Dict[str, Any], results: List[Dict[str, str]]) -> None:
        """
        Store citations in meta so orchestrator can return them.
        """
        if not isinstance(meta, dict):
            return
        if "citations" not in meta or not isinstance(meta.get("citations"), list):
            meta["citations"] = []
        # Replace (not extend) so a single provider call doesn't accumulate old citations
        meta["citations"] = results

    def _append_sources_block(self, content: str, results: List[Dict[str, str]], max_sources: int = 8) -> str:
        """
        If the model references [1], [2], etc. but doesn't include URLs,
        append a readable Sources block.
        """
        if not results:
            return content.strip()

        # If content already contains obvious URLs, still append sources, but keep it tidy.
        trimmed = content.strip()

        # Detect whether the assistant used bracket-style references like [1], [2]
        used_brackets = bool(re.search(r"\[\d+\]", trimmed))

        # Build sources text
        lines: List[str] = []
        lines.append("Sources:")
        for i, r in enumerate(results[:max_sources], start=1):
            title = (r.get("title") or "").strip() or "Source"
            url = (r.get("url") or "").strip()
            date = (r.get("date") or "").strip()

            if date:
                if url:
                    lines.append(f"[{i}] {title} ({date}) — {url}")
                else:
                    lines.append(f"[{i}] {title} ({date})")
            else:
                if url:
                    lines.append(f"[{i}] {title} — {url}")
                else:
                    lines.append(f"[{i}] {title}")

        # If the content didn't use bracket refs, keep sources separated but still present.
        spacer = "\n\n" if trimmed else ""
        if used_brackets:
            return f"{trimmed}{spacer}\n" + "\n".join(lines)
        return f"{trimmed}{spacer}\n" + "\n".join(lines)

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.perplexity_api_key:
            raise ProviderError("PERPLEXITY_API_KEY not set")

        base_url = (settings.perplexity_base_url or "https://api.perplexity.ai").rstrip("/")
        url = f"{base_url}/chat/completions"

        today = meta.get("today_utc", "unknown")
        want_citations = bool(meta.get("features", {}).get("citations", False)) or (intent == "WEB_RESEARCH_CITATIONS")

        # NOTE: For LIVE_FRESH, we want the model to use web results and present sources.
        system_prompt = (
            "You are Seekle (Ask Everyone). Answer the user clearly and helpfully.\n"
            f"Today's date (UTC) is {today}. If the user asks for today's date, use that.\n"
            "For follow-up questions, infer missing context from the conversation.\n"
            "Do not ask unnecessary clarification questions if the context is already present.\n"
            "If the question is time-sensitive, rely on retrieved web sources.\n"
        )
        if want_citations or intent == "LIVE_FRESH":
            system_prompt += (
                "Include citations by using bracket numbers like [1] [2] in the text where relevant.\n"
                "Ensure your answer is grounded in the retrieved sources.\n"
            )

        orch_system = self._extract_orchestrator_system(meta)
        if orch_system:
            system_prompt += "\n---\nConversation State:\n" + orch_system

        max_tokens = int(meta.get("max_tokens") or 800)
        max_tokens = max(64, min(max_tokens, 4000))

        messages = [{"role": "system", "content": system_prompt}] + self._build_non_system_messages(meta, query)

        payload: Dict[str, Any] = {
            "model": settings.perplexity_model or "sonar-pro",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {settings.perplexity_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise ProviderError("Perplexity request timed out")
        except Exception as e:
            raise ProviderError(f"Perplexity request failed: {type(e).__name__}") from e

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
                raise ProviderError("Perplexity quota/rate limit hit (429).") from e
            raise ProviderError(f"Perplexity HTTP {status}: {body}") from e

        try:
            data = r.json()
            content = (data["choices"][0]["message"]["content"] or "").strip()

            # Pull sources from Perplexity-specific field
            results = self._normalize_search_results(data)

            # Store in meta so orchestrator can return citations separately
            self._attach_citations(meta, results)

            # Append readable sources so users see URLs instead of only [1][2]
            if intent in ("LIVE_FRESH", "WEB_RESEARCH_CITATIONS") or want_citations:
                content = self._append_sources_block(content, results, max_sources=8)

            return content.strip()

        except Exception as e:
            raise ProviderError("Perplexity response parsing error") from e
