from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

# ----------------------------
# Tier policy defaults
# (keep these conservative; you can later move to env via config.py)
# ----------------------------

DEFAULT_FREE_DAILY_CAP = 10       # your free tier cap (separate from "free_daily_limit" before credits kick in)
DEFAULT_PAID_DAILY_CAP = 50       # you wanted a paid cap until patterns are trusted
DEFAULT_FREE_MAX_TOKENS = 500
DEFAULT_PAID_MAX_TOKENS = 900


def daily_limit_for_user(*, is_paid: bool) -> int:
    """
    Hard daily cap (anti-abuse). This is NOT the same as "free_daily_limit"
    (the number of free queries before credits are required).
    """
    return DEFAULT_PAID_DAILY_CAP if is_paid else DEFAULT_FREE_DAILY_CAP


def max_tokens_for_tier(*, is_paid: bool) -> int:
    """
    Max completion/output tokens per response by tier.
    Providers should read meta["max_tokens"] and enforce if supported.
    """
    return DEFAULT_PAID_MAX_TOKENS if is_paid else DEFAULT_FREE_MAX_TOKENS


# ----------------------------
# Provider circuit-breaker (cooldown)
# ----------------------------

# provider -> available_after UTC timestamp
_PROVIDER_COOLDOWN: Dict[str, datetime] = {}


def cooldown_provider(provider: str, minutes: int = 10) -> None:
    """
    Put a provider on cooldown after 429/quota/rate-limit events.
    """
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
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
