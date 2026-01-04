# app/db/billing_repo.py
import uuid
from sqlalchemy import text
from sqlalchemy.orm import Session


def ensure_wallet_and_plan(db: Session, user_id: uuid.UUID) -> None:
    # wallet
    db.execute(
        text(
            "insert into credit_wallets (user_id, balance_credits) "
            "values (:u, 0) "
            "on conflict (user_id) do nothing"
        ),
        {"u": user_id},
    )
    # plan
    db.execute(
        text(
            "insert into user_plans (user_id, plan) "
            "values (:u, 'free') "
            "on conflict (user_id) do nothing"
        ),
        {"u": user_id},
    )
    db.commit()


def get_user_plan(db: Session, user_id: uuid.UUID) -> str:
    row = db.execute(
        text("select plan from user_plans where user_id=:u"),
        {"u": user_id},
    ).fetchone()
    return str(row[0]) if row and row[0] else "free"


def set_user_plan(db: Session, user_id: uuid.UUID, plan: str) -> None:
    db.execute(
        text(
            "insert into user_plans (user_id, plan) values (:u, :p) "
            "on conflict (user_id) do update set plan=excluded.plan, updated_at=now()"
        ),
        {"u": user_id, "p": plan},
    )
    db.commit()


def get_balance(db: Session, user_id: uuid.UUID) -> int:
    row = db.execute(
        text("select balance_credits from credit_wallets where user_id=:u"),
        {"u": user_id},
    ).fetchone()
    return int(row[0]) if row else 0


def grant_credits(db: Session, user_id: uuid.UUID, amount: int, *, reason: str, ref: str | None = None) -> bool:
    """
    Grant credits and write a txn row.
    Idempotent if you pass (reason, ref) and have uq_credit_txns_reason_ref.
    Returns True if granted now, False if it was a duplicate.
    """
    if amount <= 0:
        return False

    ensure_wallet_and_plan(db, user_id)

    # Insert txn first (idempotent)
    res = db.execute(
        text(
            "insert into credit_txns (txn_id, user_id, delta_credits, reason, ref) "
            "values (:id, :u, :d, :r, :ref) "
            "on conflict (reason, ref) do nothing"
        ),
        {"id": str(uuid.uuid4()), "u": user_id, "d": amount, "r": reason, "ref": ref},
    )

    inserted = getattr(res, "rowcount", 0) == 1
    if not inserted:
        db.rollback()
        return False

    db.execute(
        text(
            "update credit_wallets "
            "set balance_credits = balance_credits + :a, updated_at = now() "
            "where user_id=:u"
        ),
        {"a": amount, "u": user_id},
    )
    db.commit()
    return True


def spend_credits(db: Session, user_id: uuid.UUID, amount: int, *, reason: str, query_id: uuid.UUID | None = None) -> bool:
    """
    Atomic spend: decrement only if enough balance.
    Writes a negative txn row (non-idempotent by default; that’s OK for usage).
    """
    if amount <= 0:
        return True

    ensure_wallet_and_plan(db, user_id)

    res = db.execute(
        text(
            "update credit_wallets "
            "set balance_credits = balance_credits - :a, updated_at = now() "
            "where user_id=:u and balance_credits >= :a"
        ),
        {"u": user_id, "a": amount},
    )

    if getattr(res, "rowcount", 0) != 1:
        db.rollback()
        return False

    db.execute(
        text(
            "insert into credit_txns (txn_id, user_id, delta_credits, reason, query_id) "
            "values (:id, :u, :d, :r, :qid)"
        ),
        {"id": str(uuid.uuid4()), "u": user_id, "d": -amount, "r": reason, "qid": str(query_id) if query_id else None},
    )
    db.commit()
    return True


def count_queries_last_24h(db: Session, user_id: uuid.UUID) -> int:
    row = db.execute(
        text(
            "select count(*) "
            "from queries q "
            "join chat_sessions s on s.session_id = q.session_id "
            "where s.user_id = :u and q.received_at >= (now() - interval '24 hours')"
        ),
        {"u": user_id},
    ).fetchone()
    return int(row[0]) if row else 0
