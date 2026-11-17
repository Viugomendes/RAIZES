"""Counts wrong attempts per address: 10 failures lock the form for 15 minutes."""
from django.core.cache import cache

LIMIT = 10
WINDOW = 15 * 60  # seconds, counted from the first failure


def _key(scope: str, ip: str) -> str:
    return f"raizes:failures:{scope}:{ip}"


def too_many(scope: str, ip: str) -> bool:
    return cache.get(_key(scope, ip), 0) >= LIMIT


def record_failure(scope: str, ip: str) -> None:
    key = _key(scope, ip)
    if cache.add(key, 1, WINDOW):
        return
    try:
        cache.incr(key)
    except ValueError:  # expired between the two calls
        cache.add(key, 1, WINDOW)


def clear(scope: str, ip: str) -> None:
    cache.delete(_key(scope, ip))
