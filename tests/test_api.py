"""Integration tests for the FastAPI service.

Uses fastapi.testclient against the real app -- these are the shapes a
customer will actually code against, so they are asserted precisely rather
than loosely.
"""
from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

import geomine.api.main as main_module
from geomine.api.limits import reset_rate_limiter
from geomine.api.main import app

client = TestClient(app)


def _audit_payload(**overrides):
    n = 40
    payload = {
        "feature_names": ["f0", "f1"],
        "X": [[float(i % 5), float((i * 3) % 7)] for i in range(n)],
        "y": [int(i % 3 == 0) for i in range(n)],
        "coords_xy": [[float(i * 1000), float((i % 4) * 1000)] for i in range(n)],
        "n_bootstrap": 15,
    }
    payload.update(overrides)
    return payload


def _score_boundary(**overrides):
    payload = {
        "boundary": {
            "type": "Polygon",
            "coordinates": [[[30.0, -19.0], [30.1, -19.0], [30.1, -19.1], [30.0, -19.0]]],
        },
        "commodity": "PGM",
    }
    payload.update(overrides)
    return payload


def test_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "GeoMine AI"
    assert "/docs" in body["docs"]


class TestBenchmarkEndpoint:
    def test_returns_a_real_certificate_not_a_placeholder(self):
        r = client.get("/v1/benchmark")
        assert r.status_code == 200
        body = r.json()
        assert body["certificate"] != "pending-recompute"
        assert len(body["certificate"]) == 64  # sha256 hex digest
        assert body["grade"] in {"A", "B", "C", "D", "F"}
        assert body["n_deposits"] == 17

    def test_scope_disclaims_the_vit_result(self):
        """The benchmark must not imply it certifies the Phase 2 ViT number
        -- that would repeat the exact overclaim this fix exists to remove.
        """
        r = client.get("/v1/benchmark")
        assert "does not" in r.json()["scope"].lower() or "not reproduce" in r.json()["scope"].lower()


class TestAuditEndpoint:
    def test_happy_path_shape(self):
        r = client.post("/v1/audit", json=_audit_payload())
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {
            "grade", "passed", "tests", "summary", "certificate", "elapsed_seconds"
        }
        assert len(body["tests"]) == 5
        for t in body["tests"]:
            assert set(t.keys()) == {"name", "passed", "score", "threshold", "detail"}
        assert len(body["certificate"]) == 64

    def test_shape_mismatch_x_y(self):
        r = client.post("/v1/audit", json=_audit_payload(y=[0, 1, 0]))
        assert r.status_code == 400

    def test_feature_names_mismatch(self):
        r = client.post("/v1/audit", json=_audit_payload(feature_names=["only_one"]))
        assert r.status_code == 400

    def test_ragged_rows_are_a_clean_400_not_a_500(self):
        payload = _audit_payload()
        payload["X"] = [[1.0, 2.0], [1.0]] + payload["X"][2:]
        r = client.post("/v1/audit", json=payload)
        assert r.status_code == 400

    def test_lon_lat_coordinates_are_a_clean_400_not_a_500(self):
        payload = _audit_payload()
        n = len(payload["y"])
        payload["coords_xy"] = [[30.0 + i * 0.001, -19.0 - i * 0.001] for i in range(n)]
        r = client.post("/v1/audit", json=payload)
        assert r.status_code == 400
        assert "longitude" in r.json()["detail"].lower()

    def test_single_class_labels_are_a_clean_400(self):
        payload = _audit_payload()
        payload["y"] = [0] * len(payload["y"])
        r = client.post("/v1/audit", json=payload)
        assert r.status_code == 400

    def test_non_finite_values_rejected(self):
        """NaN cannot be sent through TestClient's json= parameter (httpx
        refuses to serialize it), but Python's json module -- and therefore
        pydantic-core, and therefore a real attacker -- accepts the bare
        NaN/Infinity tokens as a documented extension to strict JSON. Send
        the raw body to exercise the actual wire format a hostile or buggy
        client can produce.
        """
        payload = _audit_payload()
        import json as _json
        raw = _json.dumps(payload).replace('"X": [[0.0', '"X": [[NaN', 1)
        r = client.post(
            "/v1/audit", content=raw, headers={"content-type": "application/json"}
        )
        assert r.status_code == 400

    def test_n_bootstrap_over_cap_rejected(self):
        r = client.post("/v1/audit", json=_audit_payload(n_bootstrap=100_000))
        assert r.status_code == 422  # pydantic validation, not our handler

    def test_n_bootstrap_zero_rejected(self):
        r = client.post("/v1/audit", json=_audit_payload(n_bootstrap=0))
        assert r.status_code == 422

    def test_nonpositive_block_size_rejected(self):
        r = client.post("/v1/audit", json=_audit_payload(block_size_km=0))
        assert r.status_code == 422

    def test_too_many_rows_rejected(self):
        n = 6000  # over MAX_ROWS
        payload = {
            "feature_names": ["f0"],
            "X": [[0.0]] * n,
            "y": [0] * n,
            "coords_xy": [[0.0, 0.0]] * n,
        }
        r = client.post("/v1/audit", json=payload)
        assert r.status_code == 422


class TestScoreEndpoint:
    def test_returns_501(self):
        r = client.post("/v1/score", json=_score_boundary())
        assert r.status_code == 501

    def test_does_not_leak_a_personal_email(self):
        r = client.post("/v1/score", json=_score_boundary())
        assert "gmail" not in r.text.lower()

    def test_invalid_polygon_type_rejected(self):
        payload = _score_boundary()
        payload["boundary"]["type"] = "Point"
        r = client.post("/v1/score", json=payload)
        assert r.status_code == 422


class TestAuthWiring:
    """Confirms X-API-Key auth is actually attached to the paid-path
    routes over real HTTP. Detailed auth logic (parsing, timing-safe
    comparison, multi-key lookup) is unit-tested in tests/test_auth.py --
    these tests exist to catch a wiring mistake (wrong dependency, wrong
    header alias, wrong endpoint) that unit tests on the bare function
    cannot see. The `real_auth` marker turns off the suite-wide auth
    bypass fixture in conftest.py for the duration of each test here.
    """
    pytestmark = pytest.mark.real_auth

    def test_audit_without_a_key_is_rejected(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_API_KEYS", "acme:secret123")
        r = client.post("/v1/audit", json=_audit_payload())
        assert r.status_code == 401

    def test_audit_with_the_configured_key_succeeds(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_API_KEYS", "acme:secret123")
        r = client.post(
            "/v1/audit", json=_audit_payload(), headers={"X-API-Key": "secret123"}
        )
        assert r.status_code == 200

    def test_score_without_a_key_is_rejected(self, monkeypatch):
        monkeypatch.delenv("GEOMINE_API_KEYS", raising=False)
        r = client.post("/v1/score", json=_score_boundary())
        assert r.status_code == 503

    def test_benchmark_stays_public(self, monkeypatch):
        monkeypatch.delenv("GEOMINE_API_KEYS", raising=False)
        r = client.get("/v1/benchmark")
        assert r.status_code == 200

    def test_health_stays_public(self, monkeypatch):
        monkeypatch.delenv("GEOMINE_API_KEYS", raising=False)
        r = client.get("/v1/health")
        assert r.status_code == 200


class TestRateLimitWiring:
    pytestmark = pytest.mark.real_auth

    def test_exceeding_the_configured_limit_returns_429(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_API_KEYS", "acme:secret123")
        reset_rate_limiter(limit=2)
        headers = {"X-API-Key": "secret123"}
        payload = _audit_payload()

        assert client.post("/v1/audit", json=payload, headers=headers).status_code == 200
        assert client.post("/v1/audit", json=payload, headers=headers).status_code == 200
        r = client.post("/v1/audit", json=payload, headers=headers)
        assert r.status_code == 429
        assert "Retry-After" in r.headers

    def test_different_keys_have_independent_budgets(self, monkeypatch):
        monkeypatch.setenv("GEOMINE_API_KEYS", "acme:secret123,beta:secret456")
        reset_rate_limiter(limit=1)
        payload = _audit_payload()

        r1 = client.post("/v1/audit", json=payload, headers={"X-API-Key": "secret123"})
        assert r1.status_code == 200
        # acme is now at its limit, but beta has not made a request yet.
        r2 = client.post("/v1/audit", json=payload, headers={"X-API-Key": "secret456"})
        assert r2.status_code == 200


class TestAuditTimeout:
    def test_an_audit_that_runs_too_long_returns_504(self, monkeypatch):
        import time as _time

        def _slow(*args, **kwargs):
            _time.sleep(0.3)
            raise AssertionError("must not be observed -- the timeout fires first")

        monkeypatch.setattr("geomine.api.main.run_audit", _slow)
        monkeypatch.setattr("geomine.api.main.AUDIT_TIMEOUT_SECONDS", 0.05)
        r = client.post("/v1/audit", json=_audit_payload())
        assert r.status_code == 504


class TestAuditConcurrencyCap:
    def test_returns_503_when_at_capacity(self, monkeypatch):
        """A slot held by a still-running (or still-orphaned-post-timeout)
        audit must block a new request, independent of rate limiting --
        this is what actually bounds concurrent CPU use, not request rate.
        """
        capped = threading.BoundedSemaphore(1)
        monkeypatch.setattr(main_module, "_audit_slots", capped)
        capped.acquire()  # simulate the one slot already being in use
        try:
            r = client.post("/v1/audit", json=_audit_payload())
            assert r.status_code == 503
        finally:
            capped.release()

    def test_a_freed_slot_is_usable_again(self, monkeypatch):
        """A single slot must serve two sequential requests, not just one --
        proving the done-callback actually releases it rather than leaking
        it on every successful audit.
        """
        capped = threading.BoundedSemaphore(1)
        monkeypatch.setattr(main_module, "_audit_slots", capped)
        payload = _audit_payload()
        assert client.post("/v1/audit", json=payload).status_code == 200
        assert client.post("/v1/audit", json=payload).status_code == 200
