# app/db/memory_repo.py
from __future__ import annotations

import json
from typing import List, Dict, Any
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


def get_state(db, session_id: str) -> Dict[str, Any]:
    row = db.execute(
        text("select state_json from session_memory where session_id=:sid"),
        {"sid": session_id},
    ).fetchone()

    raw = (row[0] if row and row[0] else "") or "{}"
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def upsert_state(db, session_id: str, state: Dict[str, Any]) -> None:
    import json

    payload = json.dumps(state or {}, ensure_ascii=False)
    db.execute(
        text(
            "insert into session_memory (session_id, state_json) values (:sid, :j) "
            "on conflict (session_id) do update set state_json=:j, updated_at=now()"
        ),
        {"sid": session_id, "j": payload},
    )
