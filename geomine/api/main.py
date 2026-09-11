"""FastAPI application for GeoMine.

This is a deliberately thin layer. The interesting work lives in
``geomine.audit`` and ``geomine.predict``. The API exists to give the product
a surface a customer can hit, and to make the validation discipline (the
moat) machine-checkable, not just a claim in a README.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Literal

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from geomine.audit import AuditConfig, audit as run_audit
from geomine.benchmark import load_manifest

MAX_ROWS = 5_000
MAX_FEATURES = 100
MAX_BOOTSTRAP = 500
"""Bounds on /v1/audit input. The endpoint refits the submitted model on the
order of 5 + 5 + n_bootstrap + 1 times synchronously inside the request, so an
unbounded n_bootstrap or row count is a trivial way to pin the server. These
are launch-stopgap bounds sized for real exploration datasets, not a
substitute for the job-queue architecture recommended for the next phase."""

logger = logging.getLogger("geomine.api")

app = FastAPI(
    title="GeoMine AI",
    description=(
        "Satellite-powered mineral targeting + model audit authority. "
        "Built on $0 infrastructure. Validated by failure."
    ),
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = Field(..., examples=["Polygon"])
    coordinates: list[list[list[float]]] = Field(..., max_length=1)


class ScoreRequest(BaseModel):
    boundary: GeoJSONPolygon
    commodity: str = Field("PGM", examples=["PGM", "Cr"])


class ScoreZone(BaseModel):
    rank: int
    centroid_lonlat: tuple[float, float]
    area_km2: float
    mean_probability: float
    confidence: float


class ScoreResponse(BaseModel):
    commodity: str
    n_zones: int
    top_zones: list[ScoreZone]
    benchmark_certificate: str
    notes: str


class AuditRequest(BaseModel):
    """Inline payload audit. Suitable for small-N exploration datasets.

    Not yet available: uploading your own model file over the API. This
    endpoint always fits and audits a standard logistic regression baseline
    against the data you submit -- it checks whether the DATA exhibits
    leakage, not a specific model of yours. To audit your own trained model,
    use the CLI: ``geomine audit data.parquet model.joblib`` (which loads a
    joblib-pickled model, so only run it against a model file you trust or
    produced yourself -- unpickling executes arbitrary code).
    """
    feature_names: list[str] = Field(..., max_length=MAX_FEATURES)
    X: list[list[float]] = Field(..., max_length=MAX_ROWS)
    y: list[int] = Field(..., max_length=MAX_ROWS)
    coords_xy: list[list[float]] = Field(
        ..., max_length=MAX_ROWS,
        description="Projected metres (e.g. UTM). NOT lon/lat.",
    )
    block_size_km: float = Field(25.0, gt=0, le=1000)
    n_bootstrap: int = Field(200, ge=1, le=MAX_BOOTSTRAP)


class AuditTest(BaseModel):
    name: str
    passed: bool
    score: float | None
    threshold: float | None
    detail: dict[str, Any] = Field(default_factory=dict)


class AuditResponse(BaseModel):
    grade: str
    passed: bool
    tests: list[AuditTest]
    summary: dict[str, Any]
    certificate: str
    elapsed_seconds: float


class BenchmarkResponse(BaseModel):
    """Pinned headline numbers for the GeoMine audit protocol benchmark.

    Scope: this certifies the AUDIT PROTOCOL end to end against real Great
    Dyke deposit coordinates and two geology-derived features. It does not
    certify the separate Phase 2 ViT research result -- see CLAIMS_AUDIT.md
    in the repository for why those are kept as distinct claims.

    Reproduce it: ``geomine audit benchmark/dataset.parquet
    benchmark/model.joblib --block-size-km 25.0``. The certificate returned
    here is loaded from a manifest computed by that exact command, not
    hardcoded, so it always reflects what the command actually produces.
    """
    model_name: str
    scope: str
    pr_auc_random_cv: float
    pr_auc_spatial_cv: float
    spatial_leakage_gap: float
    n_samples: int
    n_deposits: int
    geographic_extent: str
    grade: str
    certificate: str
    how_to_verify: str
    last_updated: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root() -> dict[str, Any]:
    return {
        "service": "GeoMine AI",
        "version": "0.1.0",
        "tagline": "Validated by failure. Audit-grade mineral targeting.",
        "docs": "/docs",
        "benchmark": "/v1/benchmark",
    }


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/benchmark", response_model=BenchmarkResponse)
def benchmark() -> BenchmarkResponse:
    """Current pinned benchmark for the GeoMine audit protocol.

    Loaded from benchmark/manifest.json, which is generated by actually
    running the audit -- never hardcoded. If this endpoint returns a 503,
    the manifest has not been built; run ``geomine benchmark build`` (or
    ``python -m geomine.benchmark``) to generate it.
    """
    manifest = load_manifest()
    if manifest is None:
        raise HTTPException(
            503,
            "Benchmark manifest not found. This endpoint refuses to serve a "
            "placeholder certificate -- run the benchmark build step first.",
        )
    s = manifest["summary"]
    return BenchmarkResponse(
        model_name=manifest["model_name"],
        scope=manifest["scope"],
        pr_auc_random_cv=s["pr_auc_random_cv"],
        pr_auc_spatial_cv=s["pr_auc_spatial_cv"],
        spatial_leakage_gap=s["spatial_leakage_gap"],
        n_samples=manifest["n_samples"],
        n_deposits=manifest["n_positives"],
        geographic_extent=manifest["geographic_extent"],
        grade=manifest["grade"],
        certificate=manifest["certificate"],
        how_to_verify=manifest["how_to_verify"],
        last_updated=manifest["generated_at"],
    )


@app.post("/v1/audit", response_model=AuditResponse)
def audit_endpoint(req: AuditRequest) -> AuditResponse:
    """Run the GeoMine audit protocol on a customer-supplied dataset.

    The customer ships their own model? Not yet -- this endpoint runs a
    standard logistic regression baseline against their data and reports
    whether the *data itself* exhibits leakage. To audit a specific model,
    use the CLI: ``geomine audit data.parquet model.joblib``.
    """
    from sklearn.linear_model import LogisticRegression

    # Validate row lengths before numpy sees them. Pydantic's list[list[float]]
    # does not enforce equal-length inner lists, so a ragged X previously hit
    # np.asarray() and raised an unhandled ValueError -- a 500 for what is a
    # client input error and should be a clean 400.
    row_lengths = {len(row) for row in req.X}
    if len(row_lengths) > 1:
        raise HTTPException(400, "X rows have inconsistent lengths")
    coord_lengths = {len(row) for row in req.coords_xy}
    if coord_lengths and coord_lengths != {2}:
        raise HTTPException(400, "coords_xy rows must each have exactly 2 values")

    X = np.asarray(req.X, dtype=np.float64)
    y = np.asarray(req.y, dtype=int)
    coords = np.asarray(req.coords_xy, dtype=np.float64)

    if X.ndim != 2 or X.shape[0] != len(y) or coords.shape != (len(y), 2):
        raise HTTPException(400, "X, y, coords_xy shape mismatch")
    if X.shape[1] != len(req.feature_names):
        raise HTTPException(400, "feature_names length must match X columns")
    if not (np.isfinite(X).all() and np.isfinite(coords).all()):
        raise HTTPException(400, "X and coords_xy must not contain NaN or infinite values")

    cfg = AuditConfig(
        block_size_km=req.block_size_km,
        n_bootstrap=req.n_bootstrap,
    )
    try:
        result = run_audit(
            LogisticRegression(max_iter=1000),
            X, y, coords,
            feature_names=req.feature_names,
            config=cfg,
        )
    except ValueError as e:
        # audit() raises ValueError for input problems it detects itself
        # (single-class labels, degree-shaped coordinates, non-binary y).
        # These are client errors, not server errors.
        raise HTTPException(400, str(e)) from e

    return AuditResponse(
        grade=result.grade,
        passed=result.passed,
        tests=[
            AuditTest(
                name=t.name, passed=t.passed,
                # NaN is preserved as null rather than coerced to 0.0. A test
                # that could not be computed (e.g. bootstrap stability on a
                # model with neither coef_ nor feature_importances_) is not
                # the same thing as a test that failed, and collapsing that
                # distinction misrepresented "not computable" as "failed" in
                # a report customers pay for.
                score=float(t.score) if math.isfinite(t.score) else None,
                threshold=float(t.threshold) if math.isfinite(t.threshold) else None,
                detail=t.detail,
            )
            for t in result.tests
        ],
        summary=result.summary,
        certificate=result.certificate,
        elapsed_seconds=result.elapsed_seconds,
    )


@app.post("/v1/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    """Score a concession boundary against the GeoMine model.

    Stub: full implementation requires the trained model + cached feature
    rasters at deploy time. Returns the structure customers will receive.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "Automated scoring is not available yet -- it requires a deployed "
            "model plus cached feature rasters per concession, which is not "
            "built. Validated extent is currently limited to the Great Dyke, "
            "Zimbabwe (see BENCHMARK.md for scope and limitations). Targeting "
            "is delivered today as a scoped engagement; see ONE_PAGER.md for "
            "contact details."
        ),
    )
