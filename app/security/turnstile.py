# app/security/turnstile.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import httpx

from app.config import settings


TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


@dataclass
class TurnstileResult:
    ok: bool
    error: Optional[str] = None
    codes: Optional[List[str]] = None
    raw: Optional[Dict[str, Any]] = None

    @property
    def reason(self) -> str:
        if self.ok:
            return "ok"
        if self.error:
            return self.error
        if self.codes:
            return f"Turnstile failed: {','.join(self.codes)}"
        return "Turnstile failed"


async def verify_turnstile(
    token: str,
    *,
    ip: Optional[str] = None,
    action: Optional[str] = None,
    cdata: Optional[str] = None,
) -> TurnstileResult:
    """
    Verify a Cloudflare Turnstile token server-side.

    token: the `cf-turnstile-response` from the client
    ip: optional client IP (can improve abuse detection)
    action: optional, if you set an action on the client widget
    cdata: optional, if you set cdata on the client widget

    Returns TurnstileResult(ok=True) if verified.
    """
    secret = getattr(settings, "turnstile_secret_key", "") or ""
    if not secret:
        # Fail closed for anonymous flows (good anti-rinse default)
        return TurnstileResult(ok=False, error="TURNSTILE_SECRET_KEY not set", codes=["missing-secret"])

    if not token:
        return TurnstileResult(ok=False, error="Missing Turnstile token", codes=["missing-input-response"])

    data: Dict[str, Any] = {
        "secret": secret,
        "response": token,
    }
    if ip:
        data["remoteip"] = ip
    if action:
        data["action"] = action
    if cdata:
        data["cdata"] = cdata

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(TURNSTILE_VERIFY_URL, data=data)
            r.raise_for_status()
            payload = r.json() if r.content else {}

        # Cloudflare response shape:
        # { success: bool, "error-codes": [...], challenge_ts, hostname, action?, cdata? }
        if payload.get("success") is True:
            # Optional hardening: if you set action/cdata on the client, enforce it here
            if action and payload.get("action") and payload.get("action") != action:
                return TurnstileResult(
                    ok=False,
                    error="Turnstile action mismatch",
                    codes=["action-mismatch"],
                    raw=payload,
                )
            if cdata and payload.get("cdata") and payload.get("cdata") != cdata:
                return TurnstileResult(
                    ok=False,
                    error="Turnstile cdata mismatch",
                    codes=["cdata-mismatch"],
                    raw=payload,
                )
            return TurnstileResult(ok=True, raw=payload)

        codes = payload.get("error-codes") or payload.get("error_codes") or []
        # Keep error concise for clients; include codes for debugging.
        return TurnstileResult(
            ok=False,
            error="Turnstile verification failed",
            codes=[str(c) for c in codes],
            raw=payload,
        )

    except httpx.HTTPStatusError as e:
        return TurnstileResult(
            ok=False,
            error=f"Turnstile HTTP {e.response.status_code}",
            codes=["http-error"],
        )


    except Exception as e:
        return TurnstileResult(
            ok=False,
            error=f"Turnstile verify error: {type(e).__name__}",
            codes=["exception"],
        )
