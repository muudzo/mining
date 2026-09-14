"""Unit tests for geomine.api.auth -- no HTTP layer involved.

FastAPI only resolves the `Header(...)` default when it builds a real
request; calling `require_api_key` directly means `x_api_key` must be
passed explicitly on every call.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from geomine.api.auth import parse_api_keys, require_api_key


class TestParseApiKeys:
    def test_single_key(self):
        assert parse_api_keys("acme:secret123") == {"secret123": "acme"}

    def test_multiple_keys(self):
        assert parse_api_keys("acme:s1,beta:s2") == {"s1": "acme", "s2": "beta"}

    def test_empty_string_yields_no_keys(self):
        assert parse_api_keys("") == {}

    def test_whitespace_is_trimmed(self):
        assert parse_api_keys(" acme : s1 , beta : s2 ") == {"s1": "acme", "s2": "beta"}

    def test_entry_missing_secret_is_skipped(self):
        assert parse_api_keys("acme:,beta:s2") == {"s2": "beta"}

    def test_entry_missing_key_id_is_skipped(self):
        assert parse_api_keys(":s1,beta:s2") == {"s2": "beta"}

    def test_entry_without_colon_is_skipped(self):
        assert parse_api_keys("not-a-pair,beta:s2") == {"s2": "beta"}

    def test_trailing_comma_is_ignored(self):
        assert parse_api_keys("acme:s1,") == {"s1": "acme"}


class TestRequireApiKey:
    def test_no_keys_configured_raises_503(self, monkeypatch):
        monkeypatch.delenv("GEOMINE_API_KEYS", raising=False)
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(x_api_key="anything")
        assert exc_info.value.status_code == 503

    def test_missing_header_raises_401(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_API_KEYS", "acme:secret123")
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(x_api_key=None)
        assert exc_info.value.status_code == 401

    def test_wrong_key_raises_401(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_API_KEYS", "acme:secret123")
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(x_api_key="wrong")
        assert exc_info.value.status_code == 401

    def test_correct_key_returns_its_id(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_API_KEYS", "acme:secret123")
        assert require_api_key(x_api_key="secret123") == "acme"

    def test_distinguishes_between_multiple_keys(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_API_KEYS", "acme:s1,beta:s2")
        assert require_api_key(x_api_key="s1") == "acme"
        assert require_api_key(x_api_key="s2") == "beta"
