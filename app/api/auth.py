import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import get_session

router = APIRouter(tags=["auth"])


@router.post("/auth/request-link")
async def request_link(email: str, session_id: str):
    db = get_session()
    if not db:
        raise HTTPException(status_code=500, detail="DB not configured")

    token = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    # Ensure session exists (in case frontend didn't call /chat/start)
    db.execute(
        text(
            "insert into chat_sessions (session_id, is_anonymous) "
            "values (:sid, true) on conflict (session_id) do nothing"
        ),
        {"sid": session_id},
    )

    # Store magic link token (no casts; pass uuid.UUID directly)
    db.execute(
        text(
            "insert into magic_links (token, email, session_id, expires_at) "
            "values (:t, :e, :s, :x)"
        ),
        {"t": token, "e": email, "s": session_id, "x": expires_at},
    )
    db.commit()
    db.close()

    # V1: print link only (later: send via Resend/Postmark)
    print(f"Magic link for {email}: https://seekle.ai/auth/verify?token={token}")

    return {"ok": True}


@router.get("/auth/verify")
async def verify(token: str):
    db = get_session()
    if not db:
        raise HTTPException(status_code=500, detail="DB not configured")

    # Parse token as UUID in Python
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
        user_id = user_row[0]  # uuid
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
