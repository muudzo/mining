"""API key authentication for the GeoMine API.

Fails closed: if no keys are configured, every endpoint that depends on
:func:`require_api_key` is unreachable rather than silently open. Configure
via the ``GEOMINE_API_KEYS`` environment variable -- never commit real
keys -- as a comma-separated list of ``key_id:secret`` pairs, e.g.::

    GEOMINE_API_KEYS="acme:sk_live_abc123,beta:sk_live_def456"

``key_id`` is never secret; it exists so logs and per-key rate limiting
(see ``geomine.api.limits``) can identify a caller without storing or
comparing the raw secret anywhere but here.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def parse_api_keys(raw: str) -> dict[str, str]:
    """Parse ``GEOMINE_API_KEYS`` syntax into ``{secret: key_id}``."""
    keys: dict[str, str] = {}
    for entry in raw.split(","):
        key_id, _, secret = entry.strip().partition(":")
        key_id, secret = key_id.strip(), secret.strip()
        if key_id and secret:
            keys[secret] = key_id
    return keys


def _configured_keys() -> dict[str, str]:
    return parse_api_keys(os.environ.get("GEOMINE_API_KEYS", ""))


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """FastAPI dependency: validate ``X-API-Key`` and return its key id.

    Every configured secret is compared with :func:`hmac.compare_digest`
    regardless of whether an earlier one already matched, so the number of
    constant-time comparisons performed does not depend on which key (if
    any) the caller holds.
    """
    keys = _configured_keys()
    if not keys:
        raise HTTPException(
            503, "API key authentication is not configured on this server."
        )
    if x_api_key is None:
        raise HTTPException(401, "Missing X-API-Key header.")

    matched_id: str | None = None
    for secret, key_id in keys.items():
        if hmac.compare_digest(secret, x_api_key):
            matched_id = key_id
    if matched_id is None:
        raise HTTPException(401, "Invalid API key.")
    return matched_id
