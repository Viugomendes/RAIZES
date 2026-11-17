"""Counts attempts per address: more than 10 in 15 minutes locks the form.

An IPv6 address counts as its /64; every /48 also has a limit of 100.

There is deliberately no limit across all addresses: anybody could then lock
the whole family out of the shared password.

The window is the timeout given to cache.add (counted from the first attempt).
The counters live in their own cache ("ratelimit" in config/settings.py), so
nothing else can push them out. With LocMemCache they live in each process: the
supported setup is a single-process server (Task 6 documents it).
"""
import ipaddress

from django.conf import settings
from django.core.cache import caches

LIMIT = 10
NETWORK_LIMIT = 100  # per IPv6 /48
WINDOW = 15 * 60  # seconds


def client_ip(request) -> str:
    """The visitor's address: the connection's, or the one given by our own proxy.

    A header is only read when RAIZES_PROXY_HEADER names it: anybody can type one.
    From X-Forwarded-For only the last entry counts, the one the proxy added.
    """
    header = settings.RAIZES_PROXY_HEADER
    value = ""
    if header == "CF-Connecting-IP":
        value = request.META.get("HTTP_CF_CONNECTING_IP", "")
    elif header == "X-Forwarded-For":
        value = request.META.get("HTTP_X_FORWARDED_FOR", "").rsplit(",", 1)[-1]
    return value.strip() or request.META.get("REMOTE_ADDR", "")


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


def counters():
    return caches["ratelimit"]


def _count(key: str) -> int:
    cache = counters()
    cache.add(key, 0, WINDOW)
    try:
        return cache.incr(key)
    except ValueError:  # expired between the two calls
        cache.add(key, 1, WINDOW)
        return 1


def attempt(scope: str, ip: str) -> bool:
    """Count one attempt, before checking anything. True when over a limit."""
    network = _network_key(scope, ip)
    # A blocked /48 is refused before its /64 gets a counter: walking through
    # new /64s must not fill the cache.
    if network is not None and _count(network) > NETWORK_LIMIT:
        return True
    return _count(_key(scope, ip)) > LIMIT


def first_time(key: str) -> bool:
    """True once per window for this key (the reset e-mail of one address)."""
    return counters().add(f"raizes:once:{key}", True, WINDOW)


def clear(scope: str, ip: str) -> None:
    """Forget the wrong attempts of this address (the /48 count runs out on its own)."""
    counters().delete(_key(scope, ip))
