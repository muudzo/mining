"""Shared fixtures for the geomine test suite.

Only depends on the audit/api extras (numpy, scipy, scikit-learn, pandas,
fastapi). Nothing here imports rasterio, geopandas or torch, so this suite
runs in CI without the geospatial or foundation-model stack installed.
"""
from __future__ import annotations

import numpy as np
import pytest

from geomine.api.limits import enforce_rate_limit, reset_rate_limiter
from geomine.api.main import app


@pytest.fixture(autouse=True)
def _api_auth_bypass(request):
    """Bypass X-API-Key auth and rate limiting for every test except ones
    marked ``real_auth``, which exist specifically to exercise that
    dependency. Also resets rate-limiter state between tests so a shared
    key id (e.g. "test-key") cannot trip the limit across unrelated tests.
    """
    reset_rate_limiter()
    if "real_auth" in request.keywords:
        yield
        return
    app.dependency_overrides[enforce_rate_limit] = lambda: "test-key"
    yield
    app.dependency_overrides.pop(enforce_rate_limit, None)


def _positional_basis(coords: np.ndarray, rng: np.random.Generator, k: int, scale: float) -> np.ndarray:
    """A bank of Gaussian bumps centred at random points.

    With a small scale and many bumps, a linear model over this basis can
    near-memorise each training point's neighbourhood -- exactly the kind of
    high-capacity positional feature a raster patch or embedding stack can
    hand a classifier by accident. Used to construct data with real,
    controllable spatial leakage.
    """
    centres = rng.uniform(0, 200_000, size=(k, 2))
    return np.stack(
        [np.exp(-((coords - c) ** 2).sum(axis=1) / (2 * scale ** 2)) for c in centres],
        axis=1,
    )


def _smooth_truth(coords: np.ndarray, rng: np.random.Generator, k: int = 6, scale: float = 35_000) -> np.ndarray:
    """A smooth, spatially continuous latent field standing in for real geology."""
    basis = _positional_basis(coords, rng, k, scale)
    weights = rng.normal(0, 1, k)
    return basis @ weights


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(0)


@pytest.fixture
def leaky_dataset():
    """A model trained on this data will look excellent under random CV and
    fail under spatial CV, by construction. High-capacity positional basis
    features let the model memorise local neighbourhoods instead of learning
    the true, weakly-weighted underlying field, which is the actual failure
    mode this codebase documented in Phase 1 (0.841 random CV -> 0.228 LOTO).
    """
    rng = np.random.default_rng(11)
    n = 500
    coords = rng.uniform(0, 200_000, size=(n, 2))
    truth = _smooth_truth(coords, np.random.default_rng(5))
    y = (truth > np.quantile(truth, 0.75)).astype(int)
    basis = _positional_basis(coords, np.random.default_rng(21), k=60, scale=6_000)
    weak_signal = 0.08 * truth + rng.normal(0, 1.5, n)
    X = np.column_stack([basis, weak_signal])
    feature_names = [f"basis_{i}" for i in range(basis.shape[1])] + ["weak_signal"]
    return {"X": X, "y": y, "coords": coords, "feature_names": feature_names}


@pytest.fixture
def clean_dataset():
    """A model trained on this data has no spatial leakage: the feature is
    the true underlying field itself (plus noise), so it generalises equally
    well to held-out geography and held-out random samples.
    """
    rng = np.random.default_rng(3)
    n = 400
    coords = rng.uniform(0, 200_000, size=(n, 2))
    truth = _smooth_truth(coords, np.random.default_rng(4), k=8, scale=25_000)
    y = (truth > np.quantile(truth, 0.7)).astype(int)
    X = np.column_stack([
        truth + rng.normal(0, 0.4, n),
        rng.normal(0, 1, n),  # an irrelevant noise feature
    ])
    return {"X": X, "y": y, "coords": coords, "feature_names": ["true_signal", "noise"]}


@pytest.fixture
def leaked_feature_dataset(clean_dataset):
    """Same geometry as clean_dataset, with one feature that is the label
    in disguise -- the exact shape of a circular feature (e.g. a feature
    computed FROM the thing being predicted, like distance-to-known-deposit).
    """
    rng = np.random.default_rng(9)
    y = clean_dataset["y"]
    leak = y.astype(float) + rng.normal(0, 0.01, len(y))
    X = np.column_stack([clean_dataset["X"], leak])
    return {
        "X": X,
        "y": y,
        "coords": clean_dataset["coords"],
        "feature_names": clean_dataset["feature_names"] + ["leaked"],
    }


@pytest.fixture
def no_skill_dataset():
    """Features carry no information about the label at all."""
    rng = np.random.default_rng(21)
    n = 300
    coords = rng.uniform(0, 200_000, size=(n, 2))
    y = (rng.uniform(0, 1, n) < 0.3).astype(int)
    X = rng.normal(0, 1, size=(n, 3))
    return {"X": X, "y": y, "coords": coords, "feature_names": ["n0", "n1", "n2"]}
