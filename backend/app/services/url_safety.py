"""SSRF guardrails for URLs that cross the backend/provider boundary."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    """Raised when a URL could target a private or unexpected network."""


def validate_external_url(url: str, *, allowed_hosts: set[str] | None = None) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeUrlError("Only absolute HTTP(S) URLs are allowed")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URLs with embedded credentials are not allowed")

    host = parsed.hostname.casefold().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise UnsafeUrlError("Local network targets are not allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise UnsafeUrlError("Private network targets are not allowed")
    if allowed_hosts is not None and host not in {item.casefold() for item in allowed_hosts}:
        raise UnsafeUrlError("URL host is not an approved provider")
    return parsed.geturl()
