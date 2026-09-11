"""Integration tests for the FastAPI service.

Uses fastapi.testclient against the real app -- these are the shapes a
customer will actually code against, so they are asserted precisely rather
than loosely.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from geomine.api.main import app

client = TestClient(app)


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
    def _payload(self, **overrides):
        n = 40
        payload = {
            "feature_names": ["f0", "f1"],
            "X": [[float(i % 5), float((i * 3) % 7)] for i in range(n)],
            "y": [i % 3 == 0 for i in range(n)],
            "y": [int(i % 3 == 0) for i in range(n)],
            "coords_xy": [[float(i * 1000), float((i % 4) * 1000)] for i in range(n)],
            "n_bootstrap": 15,
        }
        payload.update(overrides)
        return payload

    def test_happy_path_shape(self):
        r = client.post("/v1/audit", json=self._payload())
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
        r = client.post("/v1/audit", json=self._payload(y=[0, 1, 0]))
        assert r.status_code == 400

    def test_feature_names_mismatch(self):
        r = client.post("/v1/audit", json=self._payload(feature_names=["only_one"]))
        assert r.status_code == 400

    def test_ragged_rows_are_a_clean_400_not_a_500(self):
        payload = self._payload()
        payload["X"] = [[1.0, 2.0], [1.0]] + payload["X"][2:]
        r = client.post("/v1/audit", json=payload)
        assert r.status_code == 400

    def test_lon_lat_coordinates_are_a_clean_400_not_a_500(self):
        payload = self._payload()
        n = len(payload["y"])
        payload["coords_xy"] = [[30.0 + i * 0.001, -19.0 - i * 0.001] for i in range(n)]
        r = client.post("/v1/audit", json=payload)
        assert r.status_code == 400
        assert "longitude" in r.json()["detail"].lower()

    def test_single_class_labels_are_a_clean_400(self):
        payload = self._payload()
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
        payload = self._payload()
        import json as _json
        raw = _json.dumps(payload).replace('"X": [[0.0', '"X": [[NaN', 1)
        r = client.post(
            "/v1/audit", content=raw, headers={"content-type": "application/json"}
        )
        assert r.status_code == 400

    def test_n_bootstrap_over_cap_rejected(self):
        r = client.post("/v1/audit", json=self._payload(n_bootstrap=100_000))
        assert r.status_code == 422  # pydantic validation, not our handler

    def test_n_bootstrap_zero_rejected(self):
        r = client.post("/v1/audit", json=self._payload(n_bootstrap=0))
        assert r.status_code == 422

    def test_nonpositive_block_size_rejected(self):
        r = client.post("/v1/audit", json=self._payload(block_size_km=0))
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
    def _boundary(self):
        return {
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[30.0, -19.0], [30.1, -19.0], [30.1, -19.1], [30.0, -19.0]]],
            },
            "commodity": "PGM",
        }

    def test_returns_501(self):
        r = client.post("/v1/score", json=self._boundary())
        assert r.status_code == 501

    def test_does_not_leak_a_personal_email(self):
        r = client.post("/v1/score", json=self._boundary())
        assert "gmail" not in r.text.lower()

    def test_invalid_polygon_type_rejected(self):
        payload = self._boundary()
        payload["boundary"]["type"] = "Point"
        r = client.post("/v1/score", json=payload)
        assert r.status_code == 422
