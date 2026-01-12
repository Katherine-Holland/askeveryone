# app/db/models_memory.py
from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Text, func
from app.db.base import Base


class SessionMemory(Base):
    __tablename__ = "session_memory"

    session_id = Column(String, primary_key=True)

    # Structured state stored as JSON (string)
    # Example: {"topic":"Moon travel","facts":["User asked about the moon"],"entities":{"destination":"moon"},...}
    state_json = Column(Text, nullable=False, default="{}")

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
