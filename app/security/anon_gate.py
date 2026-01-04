from __future__ import annotations

import hashlib
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


def build_anon_key(*, ip: Optional[str], user_agent: Optional[str]) -> str:
    """
    Privacy-safe: hash(IP + UA + salt). No raw IP stored.
    """
    raw = f"{ip or 'noip'}|{user_agent or 'noua'}|{settings.anon_key_salt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def anon_allowance_used_last_24h(db: Session, key_hash: str) -> int:
    row = db.execute(
        text(
            "select used_count from anon_allowances "
            "where key_hash=:k and last_seen_at >= (now() - interval '24 hours')"
        ),
        {"k": key_hash},
    ).fetchone()
    return int(row[0]) if row else 0


def record_anon_use(db: Session, key_hash: str) -> None:
    """
    Upsert + increment, and bump last_seen_at.
    """
    db.execute(
        text(
            "insert into anon_allowances (key_hash, used_count, first_seen_at, last_seen_at) "
            "values (:k, 1, now(), now()) "
            "on conflict (key_hash) do update set "
            "  used_count = case "
            "    when anon_allowances.last_seen_at < (now() - interval '24 hours') then 1 "
            "    else anon_allowances.used_count + 1 "
            "  end, "
            "  last_seen_at = now()"
        ),
        {"k": key_hash},
    )
