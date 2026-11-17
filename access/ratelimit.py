"""Counts attempts per address: more than 10 in 15 minutes locks the form.

There is deliberately no limit across all addresses: anybody could then lock
the whole family out of the shared password.

The window is the timeout given to cache.add (counted from the first attempt).
With LocMemCache the counter lives in each process: the supported setup is a
single-process server (Task 6 documents it).
"""
import ipaddress

from django.core.cache import cache

LIMIT = 10
WINDOW = 15 * 60  # seconds


def _key(scope: str, ip: str) -> str:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        address = None
    if address is not None and address.version == 6:
        # One IPv6 client usually owns a whole /64: count it as one address.
        ip = str(ipaddress.ip_network(f"{address}/64", strict=False))
    return f"raizes:attempts:{scope}:{ip}"


def attempt(scope: str, ip: str) -> bool:
    """Count one attempt, before checking anything. True when over the limit."""
    key = _key(scope, ip)
    cache.add(key, 0, WINDOW)
    try:
        count = cache.incr(key)
    except ValueError:  # expired between the two calls
        cache.add(key, 1, WINDOW)
        count = 1
    return count > LIMIT


def record_failure(scope: str, ip: str) -> None:
    attempt(scope, ip)


def too_many(scope: str, ip: str) -> bool:
    return cache.get(_key(scope, ip), 0) >= LIMIT


def clear(scope: str, ip: str) -> None:
    cache.delete(_key(scope, ip))
