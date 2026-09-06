"""Decide whether a capture URL should use local-only classification."""

from __future__ import annotations

from urllib.parse import urlparse


def normalize_domain_pattern(pattern: str) -> str:
    value = pattern.strip().casefold()
    if value.startswith("https://"):
        value = value[len("https://") :]
    elif value.startswith("http://"):
        value = value[len("http://") :]
    value = value.split("/", 1)[0]
    if value.startswith("*."):
        value = value[2:]
    #  ".gov" and "gov." both mean the public suffix / label "gov".
    return value.strip(".")


def hostname_of(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return host.casefold().rstrip(".")


def matches_local_domain(url: str, patterns: list[str]) -> bool:
    """True when the URL's hostname equals or is a subdomain of a pattern."""
    host = hostname_of(url)
    if not host:
        return False
    for raw in patterns:
        pattern = normalize_domain_pattern(raw)
        if not pattern:
            continue
        if host == pattern or host.endswith(f".{pattern}"):
            return True
    return False
