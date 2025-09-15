# services/proxy_manager.py
from __future__ import annotations

import itertools
import logging
import random
from typing import Optional, List

from config import PROXY_URL, PROXY_URLS, PROXY_PATTERN, PROXY_POOL_SIZE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Build proxy pool from config:
# - PROXY_URL: single fixed proxy
# - PROXY_URLS: CSV list of proxies
# - PROXY_PATTERN + PROXY_POOL_SIZE: pattern like "http://user-{{i}}:pass@host:port"
# ---------------------------------------------------------------------------

_pool: List[str] = []

if PROXY_URL:
    _pool = [PROXY_URL.strip()]
elif PROXY_URLS:
    _pool = [u.strip() for u in PROXY_URLS.split(",") if u.strip()]
elif PROXY_PATTERN and PROXY_POOL_SIZE:
    # Replace "{{i}}" with 1..N
    _pool = [PROXY_PATTERN.replace("{{i}}", str(i)) for i in range(1, PROXY_POOL_SIZE + 1)]

_cycle = itertools.cycle(_pool) if _pool else None


def pool() -> List[str]:
    """Return a copy of the current proxy pool."""
    return list(_pool)


def get_proxy_url(round_robin: bool = True) -> Optional[str]:
    """
    Return a proxy URL string (or None if no proxies configured).
    - round_robin=True will iterate through the pool in order.
    - round_robin=False will choose a random proxy each time.
    """
    if not _pool:
        return None
    if round_robin and _cycle:
        try:
            url = next(_cycle)
        except StopIteration:  # pragma: no cover
            # Shouldn't happen with itertools.cycle, but guard anyway
            url = random.choice(_pool)
    else:
        url = random.choice(_pool)
    return url


def get_proxy() -> Optional[str]:
    """
    Alias used by callers: returns a proxy URL via round-robin (or None).
    """
    return get_proxy_url(round_robin=True)


def get_random_proxy() -> Optional[str]:
    """
    Backwards-compat alias for older imports.
    Returns a random proxy URL (or None).
    """
    return get_proxy_url(round_robin=False)


def aiohttp_proxy_kwargs() -> dict:
    """
    Convenience helper for aiohttp:
        async with aiohttp.ClientSession() as s:
            await s.get(url, **aiohttp_proxy_kwargs())
    """
    url = get_proxy()
    return {"proxy": url} if url else {}


__all__ = [
    "pool",
    "get_proxy_url",
    "get_proxy",
    "get_random_proxy",
    "aiohttp_proxy_kwargs",
]

