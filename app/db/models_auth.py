import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    is_anonymous = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
