import uuid
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, Float, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID

class Base(DeclarativeBase):
    pass

class QueryLog(Base):
    __tablename__ = "queries"

    query_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    query_text: Mapped[str] = mapped_column(Text, nullable=False)

    features_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pre_intent_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    router_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    router_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    multi_call: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    providers_called_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    provider_used_final: Mapped[str | None] = mapped_column(String(128), nullable=True)

    latency_total_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_cost_estimate_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    answered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_feedback: Mapped[str | None] = mapped_column(String(16), nullable=True)  # later: up/down
    response_mode: Mapped[str] = mapped_column(String(16), default="text", nullable=False)

    meta_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    provider_calls: Mapped[list["ProviderCall"]] = relationship(back_populates="query", cascade="all, delete-orphan")

class ProviderCall(Base):
    __tablename__ = "provider_calls"

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("queries.query_id"), nullable=False)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)

    token_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimate_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    answer_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    query: Mapped["QueryLog"] = relationship(back_populates="provider_calls")
