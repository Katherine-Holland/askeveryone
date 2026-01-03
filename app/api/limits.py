from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

# provider -> available_after UTC timestamp
_PROVIDER_COOLDOWN: Dict[str, datetime] = {}


def cooldown_provider(provider: str, minutes: int = 10) -> None:
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    _PROVIDER_COOLDOWN[provider] = until


def is_provider_available(provider: str) -> bool:
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
