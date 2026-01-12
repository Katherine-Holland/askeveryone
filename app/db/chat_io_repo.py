# app/db/chat_io_repo.py
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text


def ensure_session(db, session_id: str, is_anonymous: bool = True) -> None:
    db.execute(
        text(
            "insert into chat_sessions (session_id, is_anonymous) "
            "values (:sid, :anon) on conflict (session_id) do nothing"
        ),
        {"sid": session_id, "anon": bool(is_anonymous)},
    )


def export_messages_jsonl(db, session_id: str, limit: int = 2000) -> str:
    """
    Export messages oldest->newest as JSONL.
    """
    rows = db.execute(
        text(
            "select role, content, created_at from messages "
            "where session_id=:sid "
            "order by created_at asc "
            "limit :lim"
        ),
        {"sid": session_id, "lim": int(limit)},
    ).fetchall()

    lines: List[str] = []
    for role, content, created_at in rows:
        obj = {
            "role": role,
            "content": content,
            "created_at": (created_at.isoformat() if created_at else None),
        }
        lines.append(json.dumps(obj, ensure_ascii=False))
    return "\n".join(lines).strip() + ("\n" if lines else "")


def _parse_jsonl(jsonl_text: str, max_messages: int) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = []
    for raw_line in (jsonl_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            # skip bad lines rather than failing whole import
            continue

        role = (obj.get("role") or "").strip().lower()
        content = (obj.get("content") or "").strip()

        if role not in ("user", "assistant", "system"):
            continue
        if not content:
            continue

        msgs.append({"role": role, "content": content})

        if len(msgs) >= max_messages:
            break

    return msgs


def import_jsonl_into_session(
    db,
    *,
    jsonl_text: str,
    session_id: str,
    max_messages: int = 200,
) -> int:
    msgs = _parse_jsonl(jsonl_text, max_messages=max_messages)
    imported = 0

    for m in msgs:
        db.execute(
            text(
                "insert into messages (message_id, session_id, role, content) "
                "values (:mid, :sid, :role, :content)"
            ),
            {
                "mid": uuid.uuid4(),
                "sid": session_id,
                "role": m["role"],
                "content": m["content"],
            },
        )
        imported += 1

    return imported


def import_text_as_system_message(db, *, text_blob: str, session_id: str) -> int:
    blob = (text_blob or "").strip()
    if not blob:
        return 0

    db.execute(
        text(
            "insert into messages (message_id, session_id, role, content) "
            "values (:mid, :sid, 'system', :content)"
        ),
        {"mid": uuid.uuid4(), "sid": session_id, "content": blob},
    )
    return 1
