# app/db/memory_repo.py
from __future__ import annotations

from typing import List, Dict, Optional, Tuple
from sqlalchemy import text


def get_recent_messages(db, session_id: str, limit: int = 16) -> List[Dict[str, str]]:
    """
    Returns messages oldest->newest, shape: [{role, content}]
    """
    rows = db.execute(
        text(
            "select role, content from messages "
            "where session_id=:sid "
            "order by created_at desc "
            "limit :lim"
        ),
        {"sid": session_id, "lim": limit},
    ).fetchall()

    return [{"role": r[0], "content": r[1]} for r in rows][::-1]


def get_recent_messages_for_summary(db, session_id: str, limit: int = 40) -> List[Dict[str, str]]:
    """
    Slightly larger window for memory updates than the normal chat context.
    """
    rows = db.execute(
        text(
            "select role, content from messages "
            "where session_id=:sid "
            "order by created_at desc "
            "limit :lim"
        ),
        {"sid": session_id, "lim": limit},
    ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows][::-1]


def get_memory(db, session_id: str) -> str:
    row = db.execute(
        text("select summary from session_memory where session_id=:sid"),
        {"sid": session_id},
    ).fetchone()
    return (row[0] if row and row[0] else "") or ""


def get_memory_and_digest(db, session_id: str) -> Tuple[str, str]:
    """
    If digest column doesn't exist, returns digest="" gracefully.
    """
    try:
        row = db.execute(
            text("select summary, digest from session_memory where session_id=:sid"),
            {"sid": session_id},
        ).fetchone()
        if not row:
            return "", ""
        summary = row[0] or ""
        digest = row[1] or ""
        return summary, digest
    except Exception:
        # digest column likely doesn't exist
        summary = get_memory(db, session_id)
        return summary, ""


def upsert_memory(db, session_id: str, summary: str, digest: Optional[str] = None) -> None:
    """
    Writes memory summary to session_memory.
    If digest column exists, store it; if not, fallback to old schema.
    """
    summary = (summary or "").strip()

    if digest is None:
        # Old schema path
        db.execute(
            text(
                "insert into session_memory (session_id, summary) values (:sid, :s) "
                "on conflict (session_id) do update set summary=:s, updated_at=now()"
            ),
            {"sid": session_id, "s": summary},
        )
        return

    # Try new schema first
    try:
        db.execute(
            text(
                "insert into session_memory (session_id, summary, digest) values (:sid, :s, :d) "
                "on conflict (session_id) do update set summary=:s, digest=:d, updated_at=now()"
            ),
            {"sid": session_id, "s": summary, "d": digest or ""},
        )
    except Exception:
        # Fallback: no digest column
        db.execute(
            text(
                "insert into session_memory (session_id, summary) values (:sid, :s) "
                "on conflict (session_id) do update set summary=:s, updated_at=now()"
            ),
            {"sid": session_id, "s": summary},
        )
