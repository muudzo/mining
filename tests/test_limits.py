"""Unit tests for geomine.api.limits -- RateLimiter and MaxBodySizeMiddleware
in isolation, no HTTP client involved. Wiring these into the real endpoints
is covered by the `real_auth`-marked tests in tests/test_api.py.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from geomine.api.limits import MaxBodySizeMiddleware, RateLimiter, _limit_from_env


class TestRateLimiter:
    def test_allows_up_to_the_limit(self):
        limiter = RateLimiter(limit=3, window_seconds=60)
        for _ in range(3):
            limiter.check("alice")  # must not raise

    def test_rejects_over_the_limit(self):
        limiter = RateLimiter(limit=2, window_seconds=60)
        limiter.check("alice")
        limiter.check("alice")
        with pytest.raises(HTTPException) as exc_info:
            limiter.check("alice")
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    def test_keys_are_independent(self):
        limiter = RateLimiter(limit=1, window_seconds=60)
        limiter.check("alice")
        limiter.check("bob")  # must not raise -- separate budget

    def test_window_expiry_allows_further_requests(self, monkeypatch):
        limiter = RateLimiter(limit=1, window_seconds=10)
        clock = [1_000.0]
        monkeypatch.setattr("geomine.api.limits.time.monotonic", lambda: clock[0])

        limiter.check("alice")
        with pytest.raises(HTTPException):
            limiter.check("alice")

        clock[0] += 11  # past the window
        limiter.check("alice")  # must not raise


class TestLimitFromEnv:
    def test_unset_falls_back_to_default(self, monkeypatch):
        from geomine.api.limits import DEFAULT_RATE_LIMIT_PER_MINUTE
        monkeypatch.delenv("GEOMINE_RATE_LIMIT_PER_MINUTE", raising=False)
        assert _limit_from_env() == DEFAULT_RATE_LIMIT_PER_MINUTE

    def test_valid_positive_value_is_used(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_RATE_LIMIT_PER_MINUTE", "7")
        assert _limit_from_env() == 7

    def test_zero_or_negative_falls_back_to_default(self, monkeypatch):
        from geomine.api.limits import DEFAULT_RATE_LIMIT_PER_MINUTE
        monkeypatch.setenv("GEOMINE_RATE_LIMIT_PER_MINUTE", "0")
        assert _limit_from_env() == DEFAULT_RATE_LIMIT_PER_MINUTE
        monkeypatch.setenv("GEOMINE_RATE_LIMIT_PER_MINUTE", "-5")
        assert _limit_from_env() == DEFAULT_RATE_LIMIT_PER_MINUTE


def _receive_for(chunks: list[bytes]):
    """A fake ASGI `receive` yielding one `http.request` message per chunk,
    with `more_body` set correctly, then an empty final message.
    """
    remaining = list(chunks)

    async def receive():
        if remaining:
            body = remaining.pop(0)
            return {"type": "http.request", "body": body, "more_body": bool(remaining)}
        return {"type": "http.request", "body": b"", "more_body": False}

    return receive


def _http_scope():
    return {"type": "http", "method": "POST", "path": "/v1/audit", "headers": []}


async def _read_full_body(receive) -> bytes:
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body", False):
            return body


class TestMaxBodySizeMiddleware:
    def test_body_within_limit_reaches_the_app(self):
        events = []

        async def inner_app(scope, receive, send):
            body = await _read_full_body(receive)
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": body})

        middleware = MaxBodySizeMiddleware(inner_app, max_bytes=1_000)
        receive = _receive_for([b"hello", b"world"])

        async def send(message):
            events.append(message)

        asyncio.run(middleware(_http_scope(), receive, send))

        start = next(e for e in events if e["type"] == "http.response.start")
        body = next(e for e in events if e["type"] == "http.response.body")
        assert start["status"] == 200
        assert body["body"] == b"helloworld"

    def test_oversized_streaming_body_returns_413(self):
        app_started = False

        async def inner_app(scope, receive, send):
            nonlocal app_started
            app_started = True
            await _read_full_body(receive)  # should never finish -- raises first

        middleware = MaxBodySizeMiddleware(inner_app, max_bytes=10)
        receive = _receive_for([b"x" * 6, b"y" * 6])  # 12 bytes total, over the cap
        events = []

        async def send(message):
            events.append(message)

        asyncio.run(middleware(_http_scope(), receive, send))

        # The cap trips mid-stream, once real bytes exceed it -- not from a
        # declared Content-Length, which this middleware no longer reads.
        assert app_started
        start = next(e for e in events if e["type"] == "http.response.start")
        assert start["status"] == 413

    def test_no_declared_length_is_still_capped(self):
        """The exact gap a Content-Length-only check misses: a body with
        no declared length (as with chunked transfer encoding) still hits
        the cap, because bytes are counted as they actually arrive.
        """
        async def inner_app(scope, receive, send):
            await _read_full_body(receive)

        middleware = MaxBodySizeMiddleware(inner_app, max_bytes=10)
        receive = _receive_for([b"z" * 20])  # no Content-Length header at all
        events = []

        async def send(message):
            events.append(message)

        asyncio.run(middleware(_http_scope(), receive, send))

        start = next(e for e in events if e["type"] == "http.response.start")
        assert start["status"] == 413

    def test_non_http_scope_passes_through_untouched(self):
        seen_scopes = []

        async def inner_app(scope, receive, send):
            seen_scopes.append(scope["type"])

        middleware = MaxBodySizeMiddleware(inner_app, max_bytes=10)
        asyncio.run(middleware({"type": "lifespan"}, None, None))
        assert seen_scopes == ["lifespan"]
