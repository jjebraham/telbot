# utils/redact.py
"""Helpers for keeping credentials out of logs."""
from urllib.parse import urlsplit


def mask_proxy(url: str | None) -> str:
    """Return a proxy URL that is safe to log: user and password are hidden.

    >>> mask_proxy("http://user:secret@1.2.3.4:8080")
    'http://***@1.2.3.4:8080'
    """
    if not url:
        return "DIRECT"
    try:
        parts = urlsplit(url)
    except ValueError:
        return "<invalid proxy url>"
    if not parts.hostname:
        return "<invalid proxy url>"
    host = parts.hostname + (f":{parts.port}" if parts.port else "")
    auth = "***@" if (parts.username or parts.password) else ""
    return f"{parts.scheme}://{auth}{host}"
