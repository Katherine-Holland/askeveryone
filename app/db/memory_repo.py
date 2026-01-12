# app/db/memory_repo.py
from __future__ import annotations

from typing import List, Dict, Optional
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

    # rows are newest->oldest, reverse
    out = [{"role": r[0], "content": r[1]} for r in rows][::-1]
    return out


def get_memory(db, session_id: str) -> str:
    row = db.execute(
        text("select summary from session_memory where session_id=:sid"),
        {"sid": session_id},
    ).fetchone()
    return (row[0] if row and row[0] else "") or ""


def upsert_memory(db, session_id: str, summary: str) -> None:
    db.execute(
        text(
            "insert into session_memory (session_id, summary) values (:sid, :s) "
            "on conflict (session_id) do update set summary=:s, updated_at=now()"
        ),
        {"sid": session_id, "s": summary},
    )
