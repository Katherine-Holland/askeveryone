# app/schemas.py
from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    session_id: str = Field(..., description="Client session UUID")

    # Optional features
    compare: bool = False
    mode: str = "text"  # future-proofing ("text" | "voice")

    # ✅ Turnstile (required for anonymous usage)
    turnstile_token: Optional[str] = Field(
        default=None,
        description="Cloudflare Turnstile token (required for anonymous users)",
    )


class AskResponse(BaseModel):
    query_id: str
    answer: str
    intent: str
    provider_used: str
    providers_called: list[str]
    confidence: float
    multi_call: bool
    meta: Dict[str, Any]
