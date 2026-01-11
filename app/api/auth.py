# app/api/auth.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.config import settings
from app.db.session import get_session

router = APIRouter(tags=["auth"])

MAGIC_LINK_TTL_MINUTES = 15


def _frontend_base_url() -> str:
    """
    Where the user should land to verify the magic link.
    Set in Render as: FRONTEND_BASE_URL=https://www.seekle.io
    """
    base = getattr(settings, "frontend_base_url", "") or getattr(settings, "FRONTEND_BASE_URL", "")
    if not base:
        base = "https://www.seekle.io"
    return base.rstrip("/")


def _magic_link_url(token: uuid.UUID) -> str:
    return f"{_frontend_base_url()}/auth/verify?token={token}"


def _get_resend_config() -> tuple[str, str]:
    resend_key = getattr(settings, "resend_api_key", "") or getattr(settings, "RESEND_API_KEY", "")
    mail_from = getattr(settings, "mail_from", "") or getattr(settings, "MAIL_FROM", "")
    return (resend_key.strip(), mail_from.strip())


async def _send_magic_link_email(*, email: str, link: str) -> None:
    """
    Uses Resend if RESEND_API_KEY + MAIL_FROM are set.

    Required env vars:
      - RESEND_API_KEY
      - MAIL_FROM  (e.g. "Seekle <no-reply@seekle.io>" or "no-reply@seekle.io")

    Notes:
      - If MAIL_FROM is not a verified sender/domain in Resend, Resend will reject.
      - We log failures server-side; we do NOT block login flow.
    """
    resend_key, mail_from = _get_resend_config()

    if not resend_key or not mail_from:
        # Not configured; caller will print link fallback.
        raise RuntimeError("Resend not configured (missing RESEND_API_KEY or MAIL_FROM)")

    # Minimal, deliverable email with both HTML + text
    subject = "Your Seekle login link"
    text_body = (
        "Sign in to Seekle\n\n"
        f"Use this link to sign in (expires in {MAGIC_LINK_TTL_MINUTES} minutes):\n{link}\n\n"
        "If you didn’t request this, you can ignore this email."
    )

    html_body = f"""
    <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.5">
      <h2 style="margin:0 0 12px">Sign in to Seekle</h2>
      <p style="margin:0 0 16px">
        Click the button below to sign in. This link expires in {MAGIC_LINK_TTL_MINUTES} minutes.
      </p>
      <p style="margin:0 0 20px">
        <a href="{link}"
           style="display:inline-block;padding:12px 16px;background:#111;color:#fff;text-decoration:none;border-radius:10px">
          Sign in
        </a>
      </p>
      <p style="margin:0;color:#666;font-size:12px">
        If you didn’t request this, you can ignore this email.
      </p>
    </div>
    """

    payload = {
        "from": mail_from,
        "to": [email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
        # Optional but useful:
        "reply_to": "support@seekle.io",
        "tags": [{"name": "type", "value": "magic_link"}],
    }

    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post("https://api.resend.com/emails", json=payload, headers=headers)

    if r.status_code >= 400:
        # This is the most important log line: it tells us exactly what Resend disliked.
        # Common: "You must verify a domain..." or "from address is not allowed"
        raise RuntimeError(f"Resend error {r.status_code}: {r.text[:1200]}")


@router.post("/auth/request-link")
async def request_link(email: str, session_id: str):
    db = get_session()
    if not db:
        raise HTTPException(status_code=500, detail="DB not configured")

    email = (email or "").strip().lower()
    if not email or "@" not in email:
        db.close()
        raise HTTPException(status_code=422, detail="Invalid email")

    if not session_id:
        db.close()
        raise HTTPException(status_code=422, detail="session_id is required")

    token = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_TTL_MINUTES)

    # Ensure session exists (in case frontend didn't call /chat/start)
    db.execute(
        text(
            "insert into chat_sessions (session_id, is_anonymous) "
            "values (:sid, true) on conflict (session_id) do nothing"
        ),
        {"sid": session_id},
    )

    # Store magic link token
    db.execute(
        text(
            "insert into magic_links (token, email, session_id, expires_at) "
            "values (:t, :e, :s, :x)"
        ),
        {"t": token, "e": email, "s": session_id, "x": expires_at},
    )
    db.commit()
    db.close()

    link = _magic_link_url(token)

    # Send email if configured, else print link (dev fallback).
    resend_key, mail_from = _get_resend_config()
    if resend_key and mail_from:
        try:
            await _send_magic_link_email(email=email, link=link)
            print(f"[auth] Magic link email sent to {email} from={mail_from}")
        except Exception as e:
            # Don't block login flow, but DO log the real failure reason.
            print(f"[auth] Email send failed: {type(e).__name__}: {e}")
            print(f"[auth] Magic link fallback for {email}: {link}")
    else:
        print(f"[auth] Magic link for {email}: {link} (email not configured)")

    # Always return ok to avoid account enumeration / deliverability probing
    return {"ok": True}


@router.get("/auth/verify")
async def verify(token: str):
    db = get_session()
    if not db:
        raise HTTPException(status_code=500, detail="DB not configured")

    try:
        token_uuid = uuid.UUID(token)
    except ValueError:
        db.close()
        raise HTTPException(status_code=400, detail="Invalid token format")

    row = db.execute(
        text(
            "select email, session_id from magic_links "
            "where token = :t and expires_at > now()"
        ),
        {"t": token_uuid},
    ).fetchone()

    if not row:
        db.close()
        raise HTTPException(status_code=400, detail="Invalid or expired link")

    email, session_id = row

    # Find existing user
    user_row = db.execute(
        text("select user_id from users where email = :e"),
        {"e": email},
    ).fetchone()

    if user_row:
        user_id = user_row[0]
    else:
        user_id = uuid.uuid4()
        db.execute(
            text("insert into users (user_id, email) values (:u, :e)"),
            {"u": user_id, "e": email},
        )

    # Claim session: attach to user + mark not anonymous
    db.execute(
        text(
            "update chat_sessions "
            "set user_id = :u, is_anonymous = false, last_seen_at = now() "
            "where session_id = :s"
        ),
        {"u": user_id, "s": session_id},
    )

    # Consume token
    db.execute(text("delete from magic_links where token = :t"), {"t": token_uuid})
    db.commit()
    db.close()

    return {"ok": True, "user_id": str(user_id), "session_id": session_id}
