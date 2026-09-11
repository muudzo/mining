"""Builds and serves the public GeoMine audit benchmark.

This module produces the artifact that makes the product's central claim
checkable: a real dataset, a real fitted model, and a certificate anyone can
reproduce by running the same audit against the same files.

Scope, stated precisely because overstating it is the exact failure mode this
module exists to prevent: this benchmark demonstrates that the AUDIT PROTOCOL
is real, reproducible, and runs end to end on real Great Dyke geography. It
uses the 17 real, named, publicly known deposit locations already committed to
this repository (``data/training/deposits.geojson``) and two features computed
from other real, committed geological data -- distance to the nearest mapped
intrusive-igneous unit and to the nearest digitised regional fault -- against
a logistic regression baseline.

It is NOT a reproduction of the Phase 2 Vision Transformer result (PR-AUC
0.453). That number comes from a different model, a different feature set
built from satellite imagery this environment does not have, and a different
cross-validation scheme, and is not audited by this protocol as things
stand -- see CLAIMS_AUDIT.md. Publishing this benchmark makes one claim true
("run the audit, get this hash") without making a claim about the ViT that
the code cannot yet support.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any

BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "benchmark"
DATASET_PATH = BENCHMARK_DIR / "dataset.parquet"
MODEL_PATH = BENCHMARK_DIR / "model.joblib"
MANIFEST_PATH = BENCHMARK_DIR / "manifest.json"

DEPOSITS_PATH = Path(__file__).resolve().parent.parent / "data/training/deposits.geojson"
MACROSTRAT_PATH = Path(__file__).resolve().parent.parent / "data/geology/macrostrat_units.json"
FAULTS_PATH = Path(__file__).resolve().parent.parent / "data/geology/zimbabwe_faults.geojson"

RANDOM_SEED = 20260910
N_BACKGROUND = 120
# A local reference point near the centre of the Great Dyke study area.
REF_LON, REF_LAT = 30.1, -19.5
METRES_PER_DEGREE_LAT = 111_320.0


def _to_local_metres(lon: float, lat: float) -> tuple[float, float]:
    """Equirectangular projection centred on the Great Dyke.

    Not a substitute for a real projected CRS (EPSG:32735/32736, which this
    data actually spans two zones of) -- the audit protocol only needs
    distances that are locally consistent, and this study area is small
    enough (roughly 2 degrees) that the distortion is well under the scale
    that matters for 25km spatial blocking. Documented rather than disguised
    as a real UTM projection.
    """
    x = (lon - REF_LON) * METRES_PER_DEGREE_LAT * math.cos(math.radians(REF_LAT))
    y = (lat - REF_LAT) * METRES_PER_DEGREE_LAT
    return x, y


def _nearest_distance_m(lon: float, lat: float, points_lonlat: list[tuple[float, float]]) -> float:
    x0, y0 = _to_local_metres(lon, lat)
    best = math.inf
    for plon, plat in points_lonlat:
        x1, y1 = _to_local_metres(plon, plat)
        d = math.hypot(x0 - x1, y0 - y1)
        if d < best:
            best = d
    return best


def _load_deposits() -> list[dict[str, Any]]:
    data = json.loads(DEPOSITS_PATH.read_text())
    return data["features"]


def _load_intrusive_points() -> list[tuple[float, float]]:
    units = json.loads(MACROSTRAT_PATH.read_text())
    return [
        (u["lng"], u["lat"])
        for u in units
        if u.get("lith") == "intrusive igneous rocks"
    ]


def _load_fault_points() -> list[tuple[float, float]]:
    data = json.loads(FAULTS_PATH.read_text())
    points: list[tuple[float, float]] = []
    for f in data["features"]:
        geom = f["geometry"]
        coords = geom["coordinates"]
        if geom["type"] == "LineString":
            points.extend((c[0], c[1]) for c in coords)
    return points


def build(seed: int = RANDOM_SEED, n_background: int = N_BACKGROUND):
    """Deterministically build the dataset, fit the model, run the audit.

    Returns (dataframe, model, audit_result). Pure function of its inputs and
    the committed geology files -- no network access, no satellite imagery.
    """
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression

    from geomine.audit import AuditConfig, audit as run_audit

    deposits = _load_deposits()
    intrusive_points = _load_intrusive_points()
    fault_points = _load_fault_points()

    lons = [f["geometry"]["coordinates"][0] for f in deposits]
    lats = [f["geometry"]["coordinates"][1] for f in deposits]
    lon_min, lon_max = min(lons) - 0.3, max(lons) + 0.3
    lat_min, lat_max = min(lats) - 0.3, max(lats) + 0.3

    rng = np.random.default_rng(seed)

    rows: list[dict[str, Any]] = []
    for f in deposits:
        lon, lat = f["geometry"]["coordinates"]
        rows.append({
            "lon": lon, "lat": lat, "label": 1,
            "name": f["properties"].get("name", ""),
            "commodity": f["properties"].get("commodity", ""),
        })

    # Background points sampled uniformly across the padded deposit bounding
    # box. Real negatives would come from field-confirmed barren ground;
    # these are an honest stand-in disclosed as such in the manifest.
    for _ in range(n_background):
        lon = rng.uniform(lon_min, lon_max)
        lat = rng.uniform(lat_min, lat_max)
        rows.append({"lon": lon, "lat": lat, "label": 0, "name": "", "commodity": ""})

    for row in rows:
        x, y = _to_local_metres(row["lon"], row["lat"])
        row["x"] = x
        row["y"] = y
        row["dist_to_intrusive_m"] = _nearest_distance_m(row["lon"], row["lat"], intrusive_points)
        row["dist_to_fault_m"] = (
            _nearest_distance_m(row["lon"], row["lat"], fault_points)
            if fault_points else float("nan")
        )

    df = pd.DataFrame(rows)
    # Scale distances to kilometres so coefficients are on a readable scale.
    df["dist_to_intrusive_km"] = df["dist_to_intrusive_m"] / 1000.0
    df["dist_to_fault_km"] = df["dist_to_fault_m"] / 1000.0

    feature_cols = ["dist_to_intrusive_km", "dist_to_fault_km"]
    dataset_df = df[["x", "y", "label", *feature_cols]].copy()

    X = dataset_df[feature_cols].to_numpy()
    y = dataset_df["label"].to_numpy().astype(int)
    coords = dataset_df[["x", "y"]].to_numpy()

    model = LogisticRegression(max_iter=1000, random_state=seed % (2**31))
    model.fit(X, y)

    cfg = AuditConfig(n_bootstrap=200, block_size_km=25.0, random_state=42)
    result = run_audit(model, X, y, coords, feature_names=feature_cols, config=cfg)

    return dataset_df, model, result


def write_artifacts() -> dict[str, Any]:
    """Build the benchmark and write dataset.parquet, model.joblib, manifest.json."""
    import joblib

    from geomine.audit.report import to_markdown

    dataset_df, model, result = build()
    BENCHMARK_DIR.mkdir(exist_ok=True)

    dataset_df.to_parquet(DATASET_PATH, index=False)
    joblib.dump(model, MODEL_PATH)

    manifest = {
        "schema_version": 1,
        "scope": (
            "Demonstrates the audit protocol end to end on real Great Dyke "
            "deposit coordinates and two geology-derived features. Does NOT "
            "reproduce or certify the separate Phase 2 ViT research result "
            "(PR-AUC 0.453) -- see CLAIMS_AUDIT.md."
        ),
        "model_name": "LogisticRegression(dist_to_intrusive_km, dist_to_fault_km)",
        "n_samples": int(len(dataset_df)),
        "n_positives": int(dataset_df["label"].sum()),
        "geographic_extent": "Great Dyke, Zimbabwe (17 real named deposits + sampled background)",
        "feature_names": ["dist_to_intrusive_km", "dist_to_fault_km"],
        "grade": result.grade,
        "passed": result.passed,
        "summary": result.summary,
        "certificate": result.certificate,
        "how_to_verify": (
            "geomine audit benchmark/dataset.parquet benchmark/model.joblib "
            "--block-size-km 25.0"
        ),
        "generated_at": "2026-09-11",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, default=str))
    (BENCHMARK_DIR / "audit_report.md").write_text(to_markdown(result, model_name="great-dyke-demo"))
    return manifest


def load_manifest() -> dict[str, Any] | None:
    if not MANIFEST_PATH.exists():
        return None
    return json.loads(MANIFEST_PATH.read_text())
