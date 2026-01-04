# app/security/anon_gate.py
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


def _utc_day_str() -> str:
    # Use UTC day boundaries
    return datetime.now(timezone.utc).date().isoformat()


def build_anon_key(*, ip: Optional[str], user_agent: Optional[str]) -> str:
    """
    Hash IP + User-Agent into a stable anon key.
    - If ip missing, use placeholder (fail-closed-ish)
    - UA truncated to keep it bounded
    """
    ip_part = (ip or "0.0.0.0").strip()
    ua_part = (user_agent or "").strip()[:256]
    raw = f"{ip_part}|{ua_part}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def anon_allowance_used_today(db: Session, key_hash: str) -> int:
    day = _utc_day_str()
    row = db.execute(
        text("select count from anon_usage where key_hash=:k and day=:d"),
        {"k": key_hash, "d": day},
    ).fetchone()
    return int(row[0]) if row else 0


def record_anon_use_today(db: Session, key_hash: str) -> None:
    """
    Increment per-key daily usage (atomic upsert).
    """
    day = _utc_day_str()
    db.execute(
        text(
            "insert into anon_usage (key_hash, day, count) values (:k, :d, 1) "
            "on conflict (key_hash, day) do update set count = anon_usage.count + 1, updated_at = now()"
        ),
        {"k": key_hash, "d": day},
    )


def anon_global_used_today(db: Session) -> int:
    day = _utc_day_str()
    row = db.execute(
        text("select count from anon_global_usage where day=:d"),
        {"d": day},
    ).fetchone()
    return int(row[0]) if row else 0


def record_anon_global_use_today(db: Session) -> None:
    """
    Increment global daily anon usage (atomic upsert).
    """
    day = _utc_day_str()
    db.execute(
        text(
            "insert into anon_global_usage (day, count) values (:d, 1) "
            "on conflict (day) do update set count = anon_global_usage.count + 1, updated_at = now()"
        ),
        {"d": day},
    )
