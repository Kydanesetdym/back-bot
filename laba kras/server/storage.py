from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, asdict
from typing import Dict, Optional


@dataclass
class User:
    first_name: str
    last_name: str | None
    username: str | None
    avatar: str | None  # data URL or external URL, None means client should use placeholder

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PinEntry:
    user: User
    expires_at: float


_pins: Dict[str, PinEntry] = {}


def _cleanup_expired(now: float | None = None) -> None:
    now = time.time() if now is None else now
    expired = [pin for pin, entry in _pins.items() if entry.expires_at <= now]
    for pin in expired:
        _pins.pop(pin, None)


def generate_pin(length: int = 4, now: float | None = None) -> str:
    _cleanup_expired(now)
    # numeric PIN with leading zeros allowed
    return "".join(secrets.choice("0123456789") for _ in range(length))


def create_pin_for_user(user: User, ttl_seconds: int = 120, length: int = 4, now: float | None = None) -> str:
    now = time.time() if now is None else now
    _cleanup_expired(now)
    # ensure uniqueness among active pins
    for _ in range(50):
        pin = generate_pin(length=length, now=now)
        if pin not in _pins:
            _pins[pin] = PinEntry(user=user, expires_at=now + ttl_seconds)
            return pin
    # fallback (very unlikely)
    pin = generate_pin(length=length, now=now)
    _pins[pin] = PinEntry(user=user, expires_at=now + ttl_seconds)
    return pin


def consume_pin(pin: str, now: float | None = None) -> Optional[User]:
    now = time.time() if now is None else now
    _cleanup_expired(now)
    entry = _pins.pop(pin, None)
    if not entry:
        return None
    if entry.expires_at <= now:
        return None
    return entry.user


def peek_pin(pin: str, now: float | None = None) -> Optional[PinEntry]:
    now = time.time() if now is None else now
    _cleanup_expired(now)
    entry = _pins.get(pin)
    if not entry or entry.expires_at <= now:
        return None
    return entry


def clear_all() -> None:
    _pins.clear()


def active_count(now: float | None = None) -> int:
    _cleanup_expired(now)
    return len(_pins)
