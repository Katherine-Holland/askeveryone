# app/db/models_billing.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class CreditWallet(Base):
    __tablename__ = "credit_wallets"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    balance_credits = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CreditTxn(Base):
    __tablename__ = "credit_txns"

    txn_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    # +credits for purchases, -credits for usage
    delta_credits = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)  # e.g. "purchase", "query", "admin_adjust"
    query_id = Column(UUID(as_uuid=True), nullable=True)

    # Optional reference for idempotency (e.g., Stripe checkout session id)
    ref = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Helps prevent duplicates for the same external event
        # (e.g. reason="purchase", ref="cs_test_...")
        UniqueConstraint("reason", "ref", name="uq_credit_txns_reason_ref"),
    )


class UserPlan(Base):
    """
    Minimal plan tracking for launch.
    - 'free' users can still buy credits.
    - 'paid' could later mean subscription perks (higher caps, etc).
    """
    __tablename__ = "user_plans"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    plan = Column(String, nullable=False, default="free")  # "free" or "paid"
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StripeEvent(Base):
    """
    Stripe webhook idempotency table: ensures we process each event once.
    """
    __tablename__ = "stripe_events"

    event_id = Column(String, primary_key=True)  # Stripe event id: evt_...
    type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_json = Column(Text, nullable=True)  # store truncated payload for debugging
