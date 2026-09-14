"""Per-key rate limiting and request-size bounds for the GeoMine API.

The rate limiter is in-memory and single-process: correct at the traffic
volume this launch targets (see LAUNCH_PLAN.md section 9 -- no
orchestration, no job queue, API keys are sufficient at this scale). A
multi-worker or multi-instance deployment needs a shared store (Redis)
instead; that is out of scope until real concurrent load makes it necessary.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from geomine.api.auth import require_api_key

DEFAULT_RATE_LIMIT_PER_MINUTE = 20
WINDOW_SECONDS = 60.0


class RateLimiter:
    """Sliding-window request counter, keyed by API key id."""

    def __init__(self, limit: int, window_seconds: float = WINDOW_SECONDS) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record a hit for ``key``, raising 429 if it is over budget.

        FastAPI runs sync path operations in a thread pool, so concurrent
        requests for the same key are a real case, not a theoretical one --
        hence the lock around the shared deque.
        """
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(self.window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    429,
                    detail="Rate limit exceeded. Try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


def _limit_from_env() -> int:
    raw = os.environ.get("GEOMINE_RATE_LIMIT_PER_MINUTE", "")
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_RATE_LIMIT_PER_MINUTE
    return value if value > 0 else DEFAULT_RATE_LIMIT_PER_MINUTE


_limiter = RateLimiter(_limit_from_env())


def enforce_rate_limit(key_id: str = Depends(require_api_key)) -> str:
    """FastAPI dependency: auth, then rate-limit, then return the key id."""
    _limiter.check(key_id)
    return key_id


def reset_rate_limiter(limit: int | None = None) -> None:
    """Test-only: replace the module-level limiter with a fresh one.

    Without this, rate-limit state persists across tests that share a key
    id, and the limit itself is fixed at import time from the environment.
    """
    global _limiter
    _limiter = RateLimiter(limit if limit is not None else _limit_from_env())


class _BodyTooLarge(Exception):
    pass


class MaxBodySizeMiddleware:
    """Reject an oversized request body as bytes actually arrive.

    This has to be a raw ASGI middleware, not Starlette's
    ``BaseHTTPMiddleware`` checking ``Content-Length``: that header is
    caller-supplied and can simply be omitted (chunked transfer encoding
    needs no declared length), and by the time FastAPI's own dependency
    resolution would reject an unauthenticated caller, it has already
    called ``await request.body()`` to validate the Pydantic body model --
    body parsing and ``Depends(...)`` auth are resolved in the same pass,
    not auth-then-body. A caller who never sends ``Content-Length`` would
    sail straight past a header-only check and force full buffering before
    ``require_api_key`` ever runs. Wrapping ``receive`` counts real bytes
    as they stream in, independent of any declared length, and aborts
    before the app finishes reading a body over the cap.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        seen = 0

        async def guarded_receive() -> Message:
            nonlocal seen
            message = await receive()
            seen += len(message.get("body", b""))
            if seen > self.max_bytes:
                raise _BodyTooLarge()
            return message

        try:
            await self.app(scope, guarded_receive, send)
        except _BodyTooLarge:
            response = JSONResponse(
                {"detail": f"Request body exceeds the {self.max_bytes}-byte limit."},
                status_code=413,
            )
            await response(scope, receive, send)
