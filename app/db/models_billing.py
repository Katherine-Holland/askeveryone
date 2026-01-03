import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
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
    reason = Column(String, nullable=False)  # e.g. "purchase", "query"
    query_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserPlan(Base):
    """
    Minimal plan tracking for launch.
    - 'free' users still may have credits.
    - 'paid' indicates they can use up to paid_daily_limit (50/day).
    """
    __tablename__ = "user_plans"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    plan = Column(String, nullable=False, default="free")  # "free" or "paid"
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
