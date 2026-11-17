"""Counts attempts per address: more than 10 in 15 minutes locks the form.

An IPv6 address counts as its /64; every /48 also has a limit of 100.

There is deliberately no limit across all addresses: anybody could then lock
the whole family out of the shared password.

The window is the timeout given to cache.add (counted from the first attempt).
With LocMemCache the counter lives in each process: the supported setup is a
single-process server (Task 6 documents it).
"""
import ipaddress

from django.core.cache import cache

LIMIT = 10
NETWORK_LIMIT = 100  # per IPv6 /48
WINDOW = 15 * 60  # seconds


def client_ip(request) -> str:
    # Only REMOTE_ADDR: X-Forwarded-For can be typed by anybody.
    return request.META.get("REMOTE_ADDR", "")


def _address(ip: str):
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if address.version == 6 and address.ipv4_mapped:
        # ::ffff:1.2.3.4 is the IPv4 client 1.2.3.4 (dual-stack server).
        return address.ipv4_mapped
    return address


def _key(scope: str, ip: str) -> str:
    address = _address(ip)
    if address is not None and address.version == 6:
        # One IPv6 client usually owns a whole /64: count it as one address.
        ip = str(ipaddress.ip_network(f"{address}/64", strict=False))
    elif address is not None:
        ip = str(address)
    return f"raizes:attempts:{scope}:{ip}"


def _network_key(scope: str, ip: str) -> str | None:
    # A /48 holds 65536 /64s: one client could move between them, so it has its own limit.
    address = _address(ip)
    if address is None or address.version != 6:
        return None
    return f"raizes:attempts:{scope}:{ipaddress.ip_network(f'{address}/48', strict=False)}"


def _count(key: str) -> int:
    cache.add(key, 0, WINDOW)
    try:
        return cache.incr(key)
    except ValueError:  # expired between the two calls
        cache.add(key, 1, WINDOW)
        return 1


def attempt(scope: str, ip: str) -> bool:
    """Count one attempt, before checking anything. True when over a limit."""
    blocked = _count(_key(scope, ip)) > LIMIT
    network = _network_key(scope, ip)
    if network is not None and _count(network) > NETWORK_LIMIT:
        blocked = True
    return blocked


def clear(scope: str, ip: str) -> None:
    """Forget the wrong attempts of this address (the /48 count runs out on its own)."""
    cache.delete(_key(scope, ip))
