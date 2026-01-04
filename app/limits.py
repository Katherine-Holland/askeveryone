# app/limits.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from app.config import settings

# ----------------------------
# Tier policy (from config/env)
# ----------------------------

def daily_limit_for_user(*, is_paid: bool) -> int:
    """
    Hard daily cap (anti-abuse). NOT the same as free_daily_limit
    (free allowance before credits are required).
    """
    return settings.paid_daily_cap if is_paid else settings.free_daily_cap


def max_tokens_for_tier(*, is_paid: bool) -> int:
    """
    Max output tokens by tier. Providers should read meta["max_tokens"].
    """
    return settings.max_tokens_paid if is_paid else settings.max_tokens_free


# ----------------------------
# Provider circuit breaker (cooldown)
# ----------------------------

_PROVIDER_COOLDOWN: Dict[str, datetime] = {}

def cooldown_provider(provider: str, minutes: Optional[int] = None) -> None:
    """
    Put a provider on cooldown after 429/quota/rate-limit events.
    minutes defaults to settings.provider_cooldown_minutes.
    """
    mins = minutes if minutes is not None else getattr(settings, "provider_cooldown_minutes", 10)
    until = datetime.now(timezone.utc) + timedelta(minutes=int(mins))
    _PROVIDER_COOLDOWN[provider] = until


def is_provider_available(provider: str) -> bool:
    """
    True if provider is not on cooldown (or cooldown has expired).
    """
    until = _PROVIDER_COOLDOWN.get(provider)
    if not until:
        return True
    return datetime.now(timezone.utc) >= until


def cooldown_remaining_seconds(provider: str) -> Optional[int]:
    until = _PROVIDER_COOLDOWN.get(provider)
    if not until:
        return None
    now = datetime.now(timezone.utc)
    if now >= until:
        return 0
    return int((until - now).total_seconds())
