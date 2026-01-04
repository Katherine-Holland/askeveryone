from __future__ import annotations
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings


def get_global_used_today(db: Session) -> int:
    row = db.execute(
        text(
            "select used from global_limits "
            "where key=:k and day=current_date"
        ),
        {"k": settings.global_free_pool_key},
    ).fetchone()
    return int(row[0]) if row else 0


def try_take_from_free_pool(db: Session, amount: int = 1) -> bool:
    """
    Atomic increment if still under the pool.
    Returns True if taken, False if exhausted.
    """
    # Ensure row exists
    db.execute(
        text(
            "insert into global_limits (key, day, used, updated_at) "
            "values (:k, current_date, 0, now()) "
            "on conflict (key, day) do nothing"
        ),
        {"k": settings.global_free_pool_key},
    )

    res = db.execute(
        text(
            "update global_limits "
            "set used = used + :a, updated_at = now() "
            "where key = :k and day = current_date and used + :a <= :cap"
        ),
        {"k": settings.global_free_pool_key, "a": amount, "cap": settings.global_free_pool_per_day},
    )

    return getattr(res, "rowcount", 0) == 1
