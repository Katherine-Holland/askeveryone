import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Boolean,
    Float,
    Text,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class QueryLog(Base):
    __tablename__ = "queries"

    query_id = UUID(as_uuid=True)
    query_id = Base.metadata.tables.get(__tablename__, None)

    # Columns
    query_id = Base.metadata.tables.get(__tablename__, None)

    # --- Core identifiers ---
    query_id = None  # type: ignore

    # SQLAlchemy Columns (classic style)
    from sqlalchemy import Column  # local import to keep file compact

    query_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(128), nullable=True)

    # NEW: attach queries to a user once session is claimed via magic link
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)

    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    query_text = Column(Text, nullable=False)

    features_json = Column(JSONB, nullable=True)
    pre_intent_hint = Column(String(64), nullable=True)
    router_intent = Column(String(64), nullable=True)
    router_confidence = Column(Float, nullable=True)
    multi_call = Column(Boolean, default=False, nullable=False)

    providers_called_json = Column(JSONB, nullable=True)
    provider_used_final = Column(String(128), nullable=True)

    latency_total_ms = Column(Integer, nullable=True)
    token_cost_estimate_usd = Column(Float, nullable=True)

    answered = Column(Boolean, default=True, nullable=False)
    user_feedback = Column(String(16), nullable=True)  # later: up/down
    response_mode = Column(String(16), default="text", nullable=False)

    meta_json = Column(JSONB, nullable=True)

    provider_calls = relationship(
        "ProviderCall",
        back_populates="query",
        cascade="all, delete-orphan",
    )


class ProviderCall(Base):
    __tablename__ = "provider_calls"

    from sqlalchemy import Column  # local import to keep file compact

    call_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.query_id"), nullable=False)

    provider = Column(String(32), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    latency_ms = Column(Integer, nullable=True)

    success = Column(Boolean, default=False, nullable=False)
    error_code = Column(String(128), nullable=True)

    token_in = Column(Integer, nullable=True)
    token_out = Column(Integer, nullable=True)
    cost_estimate_usd = Column(Float, nullable=True)

    answer_excerpt = Column(Text, nullable=True)

    query = relationship("QueryLog", back_populates="provider_calls")
