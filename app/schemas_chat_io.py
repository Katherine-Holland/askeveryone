# app/schemas_chat_io.py
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List, Literal


Role = Literal["user", "assistant", "system"]


class ImportChatRequest(BaseModel):
    """
    Accept either:
      - jsonl: a JSONL string where each line is {"role":"user|assistant|system","content":"...","created_at":"...optional..."}
      - text: a plain text transcript (we'll store it as a single system message)
    """
    jsonl: Optional[str] = None
    text: Optional[str] = None

    # If you want to attach to an existing session_id instead of creating a new one:
    session_id: Optional[str] = None

    # Mark imported session as anonymous by default (can be claimed later via magic link flow)
    is_anonymous: bool = True

    # Optional: cap imported lines to prevent abuse
    max_messages: int = Field(default=200, ge=1, le=2000)


class ImportChatResponse(BaseModel):
    ok: bool
    session_id: str
    imported_messages: int
