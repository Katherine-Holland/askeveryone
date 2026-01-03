from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
import uuid


def ensure_wallet_and_plan(db: Session, user_id):
    # wallet
    db.execute(
        text("insert into credit_wallets (user_id, balance_credits) values (:u, 0) "
             "on conflict (user_id) do nothing"),
        {"u": user_id},
    )
    # plan
    db.execute(
        text("insert into user_plans (user_id, plan) values (:u, 'free') "
             "on conflict (user_id) do nothing"),
        {"u": user_id},
    )
    db.commit()


def get_user_plan(db: Session, user_id) -> str:
    row = db.execute(text("select plan from user_plans where user_id=:u"), {"u": user_id}).fetchone()
    return row[0] if row else "free"


def get_wallet_balance(db: Session, user_id) -> int:
    row = db.execute(
        text("select balance_credits from credit_wallets where user_id=:u"),
        {"u": user_id},
    ).fetchone()
    return int(row[0]) if row else 0


def add_credits(db: Session, user_id, credits: int, reason: str = "purchase"):
    ensure_wallet_and_plan(db, user_id)
    db.execute(
        text("update credit_wallets set balance_credits = balance_credits + :c, updated_at=now() where user_id=:u"),
        {"c": credits, "u": user_id},
    )
    db.execute(
        text("insert into credit_txns (txn_id, user_id, delta_credits, reason, query_id) "
             "values (:t, :u, :d, :r, :q)"),
        {"t": uuid.uuid4(), "u": user_id, "d": credits, "r": reason, "q": None},
    )
    db.commit()


def spend_credits(db: Session, user_id, credits: int, query_id, reason: str = "query") -> bool:
    """
    Returns True if spent, False if insufficient funds.
    """
    ensure_wallet_and_plan(db, user_id)
    bal = get_wallet_balance(db, user_id)
    if bal < credits:
        return False

    db.execute(
        text("update credit_wallets set balance_credits = balance_credits - :c, updated_at=now() where user_id=:u"),
        {"c": credits, "u": user_id},
    )
    db.execute(
        text("insert into credit_txns (txn_id, user_id, delta_credits, reason, query_id) "
             "values (:t, :u, :d, :r, :q)"),
        {"t": uuid.uuid4(), "u": user_id, "d": -credits, "r": reason, "q": query_id},
    )
    db.commit()
    return True


def count_queries_last_24h(db: Session, *, user_id=None, session_id=None) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    if user_id:
        row = db.execute(
            text("select count(*) from query_logs where user_id=:u and created_at >= :since"),
            {"u": user_id, "since": since},
        ).fetchone()
    else:
        row = db.execute(
            text("select count(*) from query_logs where session_id=:s and created_at >= :since"),
            {"s": session_id, "since": since},
        ).fetchone()
    return int(row[0]) if row else 0
