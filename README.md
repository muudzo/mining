# GeoMine AI

**An independent audit protocol for mineral-exploration machine learning, plus a
satellite-based prospectivity pipeline for the Great Dyke, Zimbabwe.**

Built on free public Earth observation data. The validation framework is the point.

---

## Why this exists

Geological data is spatially autocorrelated: deposits sit near other deposits. Score a
prospectivity model with ordinary random cross-validation and you measure how well it
memorised the neighbourhood of its training points, not whether it can find anything new.
The inflation is not subtle.

We measured it on our own model:

| Validation method | PR-AUC |
|---|---|
| Random 5-fold CV | 0.841 |
| Leave-one-tile-out CV | 0.228 |
| Class prior (no-skill floor) | 0.226 |

The number almost everyone publishes was 0.841. The honest number was 0.228 -- no better than
guessing. **The gap between those two numbers is the entire problem this project addresses.**

We published that failure rather than the flattering number, then rebuilt. The module that
caught it is the module offered here for auditing anyone else's model.

---

## Two things live in this repository

### 1. `geomine.audit` -- the audit protocol

Takes any scikit-learn-compatible binary classifier and a labelled, spatially-referenced
dataset. Runs five tests and returns a graded result plus a content-addressed certificate.

| # | Test | Fails when |
|---|---|---|
| 1 | Spatial leakage | Random-CV PR-AUC exceeds spatial-block-CV PR-AUC by more than 0.30 |
| 2 | Class prior | Spatial-CV PR-AUC does not beat the positive rate in the data |
| 3 | Bootstrap stability | Coefficient or importance signs flip across resamples |
| 4 | Calibration | Expected calibration error above 0.10 on a held-out fold |
| 5 | Feature-label leakage | Any feature correlates with the label at \|r\| >= 0.95 |

Any failure fails the audit. The protocol is public and the thresholds are public, so the
grade can be argued with. That is deliberate.

### 2. The prospectivity pipeline

Download, preprocess, feature-engineer, train, validate and predict over Sentinel-2, ASTER and
Copernicus DEM data. Spectral indices, terrain and structural features, spatial cross-validation
respecting the Great Dyke's linear geometry, SHAP attribution, uncertainty and target clustering.

---

## Install

Requires Python 3.11 or newer. The geospatial stack depends on GDAL, which is easiest to obtain
through conda on macOS.

```bash
# Audit + API only -- lean, no GDAL required
pip install -e ".[api,audit]"

# Full pipeline including raster processing
pip install -e ".[api,audit,dev]"
```

## Quickstart -- audit a model

```python
import numpy as np
from sklearn.linear_model import LogisticRegression
from geomine.audit import audit

# X: (n_samples, n_features)
# y: binary 0/1 labels
# coords: (n_samples, 2) in PROJECTED METRES, e.g. UTM -- not lon/lat
result = audit(
    LogisticRegression(max_iter=1000),
    X, y, coords,
    feature_names=["ferric_iron", "slope", "fault_distance"],
)

print(result.grade)        # A-F
print(result.passed)       # True only if all five tests pass
print(result.certificate)  # sha256 over inputs and results
for t in result.tests:
    print(f"{t.name:24} {'PASS' if t.passed else 'FAIL'}  {t.score:.3f} (threshold {t.threshold})")
```

Coordinates **must** be projected metres. Passing degrees produces meaningless spatial blocks
and an audit that silently measures nothing.

### Command line

```bash
geomine audit dataset.parquet model.joblib --output audit.md --json-output audit.json
```

> **Security note.** `model.joblib` is loaded with `joblib.load`, which unpickles and therefore
> executes arbitrary code. Only audit model files you trust or produced yourself. Do not run
> this against a file emailed to you by a third party.

### API

```bash
uvicorn geomine.api.main:app --port 8000
curl http://localhost:8000/v1/benchmark
```

Interactive documentation at `/docs`. Endpoints: `/v1/health`, `/v1/benchmark`, `/v1/audit`.
`/v1/score` returns 501 -- concession scoring is currently delivered as a per-engagement
service rather than self-serve, because it requires deployed models and cached feature rasters.

---

## Current model performance

| Metric | Value |
|---|---|
| PR-AUC, random 5-fold CV | 0.612 |
| **PR-AUC, leave-one-tile-out CV** | **0.453** |
| Spatial leakage gap | 0.159 |
| Class prior baseline | 0.226 |
| Labelled deposits | 17 |
| Geographic extent | Great Dyke, Zimbabwe -- 4 Sentinel-2 tiles |
| Model | Prithvi-EO-2.0 ViT, fine-tuned |

**How much weight this number carries.** It rests on 17 labelled deposits in a single geology.
That is enough to demonstrate that cross-tile signal exists where our earlier spectral models
had none. It is not enough to quote to three decimal places with confidence, and the honest
uncertainty interval around it is wide. Treat it as a promising research result rather than a
production guarantee, and see [BENCHMARK.md](BENCHMARK.md) for full history including the
configurations that failed.

### Reproducing it

A pinned benchmark dataset and model artifact, together with the published certificate hash,
are **in preparation** and are not yet in this repository. Until they are here, the number
above is a reported result, not an independently verifiable one, and we would rather say so
than imply otherwise. Progress on this is tracked as the first blocker in
[LAUNCH_PLAN.md](LAUNCH_PLAN.md).

Hash reproducibility currently holds within a single environment. Reproducing a certificate
across different machines, BLAS backends or library versions is not yet guaranteed.

---

## What this is not

- **Not a discovery guarantee.** PR-AUC measures ranking quality against known labelled
  deposits. It does not predict exploration outcomes.
- **Not transferable between geologies.** This model was trained on the Great Dyke. Another
  orogen needs another model and another audit.
- **Not a replacement for fieldwork.** Probability maps narrow where to look. Drilling
  determines what is there.

---

## Project layout

```
geomine/
  audit/        The audit protocol -- five tests, grading, certificates
  api/          FastAPI service
  cli.py        download / compute-features / train / predict / audit / layers
  ingest/       Sentinel-2, ASTER, Copernicus DEM, USGS MRDS
  spectral/     Spectral indices and geological band composites
  structural/   Terrain, lineaments, proximity
  training/     Spatial CV, along-strike CV, baselines, SHAP
  predict/      Chunked raster inference, uncertainty, target clustering
scripts/        Pipeline execution and foundation-model training
configs/        Study area and pipeline parameters
```

## Documentation

| Document | Contents |
|---|---|
| [BENCHMARK.md](BENCHMARK.md) | Pinned metrics, audit protocol, full benchmark history |
| [LAUNCH_PLAN.md](LAUNCH_PLAN.md) | Commercial launch plan, blockers, timeline |
| [GEOMINE_AI.md](GEOMINE_AI.md) | Technical whitepaper |
| [PHASE1_POSTMORTEM.md](PHASE1_POSTMORTEM.md) | Why the first approach failed |
| [PHASE2_PIVOT.md](PHASE2_PIVOT.md) | Eight failed configurations and the pivot rationale |
| [OVERVIEW.md](OVERVIEW.md) | Plain-language explanation and technology stack |

## Data sources

Sentinel-2 L2A (ESA Copernicus), ASTER (NASA EarthData), Copernicus DEM 30m (AWS Open Data),
Macrostrat, GEM Active Faults, USGS MRDS. All free and public.

## Contact

GeoMine AI Project -- see [ONE_PAGER.md](ONE_PAGER.md) for commercial enquiries.
