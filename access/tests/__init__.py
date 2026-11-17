from django.core.cache import caches


def clear_caches():
    """Empty every cache: the default one and the attempt counters (access/ratelimit.py)."""
    for cache in caches.all():
        cache.clear()
