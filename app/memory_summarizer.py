# app/memory_summarizer.py
from __future__ import annotations

import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple

import httpx

from app.config import settings


def _sha256_text(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _clamp(n: int, lo: int, hi: int) -> int:
    try:
        n = int(n)
    except Exception:
        n = lo
    return max(lo, min(hi, n))


def build_transcript(messages: List[Dict[str, str]], max_chars: int = 9000) -> str:
    """
    Build a compact transcript like:
      U: ...
      A: ...
    for summarisation. We cap by chars to avoid giant prompts.
    """
    lines: List[str] = []
    for m in messages:
        role = (m.get("role") or "").strip().lower()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            prefix = "U:"
        elif role == "assistant":
            prefix = "A:"
        else:
            continue
        lines.append(f"{prefix} {content}")
    txt = "\n".join(lines).strip()
    if len(txt) > max_chars:
        txt = txt[-max_chars:]  # keep most recent chunk
    return txt


def build_memory_prompt(
    *,
    previous_memory: str,
    transcript: str,
    today_utc: str,
) -> str:
    """
    Strict grounding prompt:
    - Only use facts explicitly in transcript
    - If user changes their mind, record latest
    - No speculation
    - Output a JSON object we can parse deterministically
    """
    prev = (previous_memory or "").strip()
    return (
        "You are a memory summariser for a multi-turn chat assistant.\n"
        "Your job: update the conversation memory using ONLY the transcript.\n\n"
        "CRITICAL RULES (MUST FOLLOW):\n"
        "1) Use ONLY information explicitly stated in the transcript. Do NOT guess.\n"
        "2) If the transcript is ambiguous, omit the detail.\n"
        "3) If the user corrects/changes something, keep the most recent version.\n"
        "4) Do NOT invent names, places, preferences, or tasks.\n"
        "5) Keep memory concise and stable: include only durable context that helps future turns.\n"
        "6) Avoid copying long text verbatim; summarize.\n\n"
        f"Today's date (UTC) is {today_utc}.\n\n"
        "Return ONLY valid JSON (no markdown) with this exact schema:\n"
        "{\n"
        '  "facts": [string, ...],\n'
        '  "open_tasks": [string, ...],\n'
        '  "decisions": [string, ...],\n'
        '  "current_context": string,\n'
        '  "do_not_assume": [string, ...]\n'
        "}\n\n"
        "Guidance on fields:\n"
        "- facts: stable user/project facts that persist (e.g. project goal, chosen plan)\n"
        "- open_tasks: next steps the user intends to do\n"
        "- decisions: explicit decisions made\n"
        "- current_context: 1–3 sentences describing what we are doing right now\n"
        "- do_not_assume: list of things the assistant must NOT assume without asking\n\n"
        "Previous Memory (may be incomplete):\n"
        f"{prev}\n\n"
        "Transcript:\n"
        f"{transcript}\n"
    )


async def summarize_with_openai(
    *,
    previous_memory: str,
    transcript: str,
    today_utc: str,
    timeout_s: float = 45.0,
) -> Tuple[str, str]:
    """
    Returns: (memory_text, digest)
    memory_text is a compact, human-readable summary created from JSON fields.
    digest is sha256 over transcript (for dedupe).
    """
    if not settings.openai_api_key:
        # If no OpenAI key, just keep previous memory unchanged.
        digest = _sha256_text(transcript)
        return (previous_memory or "").strip(), digest

    digest = _sha256_text(transcript)

    # Keep this cheap: small output, deterministic.
    max_tokens = _clamp(int(getattr(settings, "memory_max_tokens", 350)), 128, 800)

    system_prompt = (
        "You are a careful, literal, grounded system. "
        "Follow instructions exactly. Output JSON only."
    )

    user_prompt = build_memory_prompt(
        previous_memory=previous_memory,
        transcript=transcript,
        today_utc=today_utc,
    )

    payload: Dict[str, Any] = {
        "model": settings.openai_answer_model,  # reuse; optionally set a dedicated MEMORY model later
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except Exception:
        # fail-open: don't break /ask
        return (previous_memory or "").strip(), digest

    if r.status_code >= 400:
        return (previous_memory or "").strip(), digest

    try:
        content = r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return (previous_memory or "").strip(), digest

    # Parse JSON strictly
    try:
        obj = json.loads(content)
        facts = obj.get("facts") or []
        tasks = obj.get("open_tasks") or []
        decisions = obj.get("decisions") or []
        ctx = (obj.get("current_context") or "").strip()
        dna = obj.get("do_not_assume") or []
    except Exception:
        # If it didn't output valid JSON, don't trust it.
        return (previous_memory or "").strip(), digest

    def _clean_list(xs: Any, max_items: int) -> List[str]:
        out: List[str] = []
        if not isinstance(xs, list):
            return out
        for x in xs:
            if not isinstance(x, str):
                continue
            s = " ".join(x.strip().split())
            if s:
                out.append(s[:240])
        # de-dup preserving order
        seen = set()
        uniq: List[str] = []
        for s in out:
            if s in seen:
                continue
            seen.add(s)
            uniq.append(s)
        return uniq[:max_items]

    facts = _clean_list(facts, 12)
    tasks = _clean_list(tasks, 10)
    decisions = _clean_list(decisions, 10)
    dna = _clean_list(dna, 10)
    ctx = " ".join(ctx.split())[:360]

    # Build final memory text (human-readable + stable formatting)
    parts: List[str] = []
    if ctx:
        parts.append(f"Current context: {ctx}")
    if facts:
        parts.append("Facts:\n- " + "\n- ".join(facts))
    if decisions:
        parts.append("Decisions:\n- " + "\n- ".join(decisions))
    if tasks:
        parts.append("Open tasks:\n- " + "\n- ".join(tasks))
    if dna:
        parts.append("Do not assume:\n- " + "\n- ".join(dna))

    memory_text = "\n\n".join(parts).strip()

    # If the model output is empty, keep old memory
    if not memory_text:
        memory_text = (previous_memory or "").strip()

    # Cap total memory
    max_chars = int(getattr(settings, "max_memory_chars", 1200))
    memory_text = memory_text[:max_chars]

    return memory_text, digest
