"""Core audit logic.

A single public entry point -- ``audit()`` -- runs the full protocol against
any sklearn-compatible binary classifier and returns a structured result.

The protocol has five tests:

  1. **Random CV vs spatial CV gap** -- detects spatial leakage. A large gap
     means the random-CV number is inflated and the model does not generalize
     across geographies.
  2. **Class-prior baseline** -- the model must beat the rate at which
     positives appear in the dataset. PR-AUC at or below the prior is no skill.
  3. **Bootstrap stability** -- resampled coefficients (LR) or feature
     importances (tree models) must keep the same sign with reasonable
     confidence interval width.
  4. **Calibration** -- predicted probabilities must track empirical positive
     rates within a bin-wise tolerance.
  5. **Feature-label leakage** -- any single feature with point-biserial
     correlation > 0.95 against the label is flagged. Real geological
     signals are rarely that strong; this usually means the label was
     leaked into the features.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable

import numpy as np
from sklearn.base import clone
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "v1"
"""Version of the audit protocol.

Embedded in every certificate. A change to any test, threshold or hashing rule
requires bumping this, so a certificate always says which protocol produced it.
"""

HASH_DECIMALS = 6
"""Precision at which floats are quantised before hashing.

Cross-validation scores are outputs of floating-point model fitting, so their
last bits depend on the BLAS backend, thread count and library versions. Drift
at that level is around 1e-12. Rounding to 1e-6 sits far above the noise and
far below any precision we would report, which is what makes the certificate
reproducible on a different machine rather than only on the one that made it.
"""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class AuditConfig:
    """Audit thresholds and toggles.

    Defaults are tuned for mineral prospectivity. Override per use case.
    """
    spatial_leakage_max_gap: float = 0.30
    """Max acceptable PR-AUC drop from random CV to spatial CV. Default 0.30."""

    block_size_km: float = 25.0
    """Edge length of spatial blocks for spatial CV. Coordinates must be in metres."""

    n_random_folds: int = 5
    n_spatial_folds: int = 5
    n_bootstrap: int = 200

    feature_leakage_threshold: float = 0.95
    """Point-biserial correlation above which a feature is flagged as leaking."""

    calibration_n_bins: int = 10
    calibration_max_ece: float = 0.10
    """Max expected calibration error."""

    random_state: int = 42

    unsigned_importance_max_rel_ci: float = 1.0
    """Stability bar for models exposing non-negative importances.

    Sign consistency is meaningless for tree-ensemble importances, which are
    non-negative by construction, so a sign test passes for every feature and
    measures nothing. For those models a feature counts as stable when the
    width of its bootstrap 95% interval is no greater than this multiple of
    its mean importance.
    """

    allow_degree_coords: bool = False
    """Permit coordinates that look like longitude/latitude.

    Spatial blocking requires projected metres. Degrees collapse every point
    into one block, which silently turns spatial CV back into no CV at all.
    The audit refuses degree-shaped coordinates unless this is set.
    """


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    threshold: float
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResult:
    passed: bool
    grade: str
    tests: list[TestResult]
    summary: dict[str, Any]
    certificate: str
    """Content hash of (config, dataset fingerprint, scores).

    Two audits with the same hash had the same inputs and produced the same
    numbers. Customers can publish the hash; auditors can re-derive it.
    """
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _spatial_blocks(coords_xy: np.ndarray, block_size_km: float) -> np.ndarray:
    block_m = block_size_km * 1000.0
    xs, ys = coords_xy[:, 0], coords_xy[:, 1]
    col = ((xs - xs.min()) / block_m).astype(int)
    row = ((ys - ys.min()) / block_m).astype(int)
    n_cols = int(col.max()) + 1
    return (row * n_cols + col).astype(int)


def _spatial_cv_score(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    block_ids: np.ndarray,
    n_folds: int,
) -> float:
    unique = np.unique(block_ids)
    if len(unique) < 2:
        return float("nan")
    n_folds = min(n_folds, len(unique))

    rng = np.random.default_rng(0)
    shuffled = rng.permutation(unique)
    fold_assign = {b: i % n_folds for i, b in enumerate(shuffled)}

    preds = np.full(len(y), np.nan)
    for fold in range(n_folds):
        test_blocks = {b for b, f in fold_assign.items() if f == fold}
        test_mask = np.array([b in test_blocks for b in block_ids])
        if test_mask.sum() == 0 or (~test_mask).sum() == 0:
            continue
        if len(np.unique(y[~test_mask])) < 2:
            continue

        m = clone(model)
        m.fit(X[~test_mask], y[~test_mask])
        preds[test_mask] = m.predict_proba(X[test_mask])[:, 1]

    valid = ~np.isnan(preds)
    if len(np.unique(y[valid])) < 2:
        return float("nan")
    return float(average_precision_score(y[valid], preds[valid]))


def _random_cv_score(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    n_folds: int,
    random_state: int,
) -> float:
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    preds = np.full(len(y), np.nan)
    for train_idx, test_idx in skf.split(X, y):
        if len(np.unique(y[train_idx])) < 2:
            continue
        m = clone(model)
        m.fit(X[train_idx], y[train_idx])
        preds[test_idx] = m.predict_proba(X[test_idx])[:, 1]

    valid = ~np.isnan(preds)
    if len(np.unique(y[valid])) < 2:
        return float("nan")
    return float(average_precision_score(y[valid], preds[valid]))


def _bootstrap_stability(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    n_bootstrap: int,
    random_state: int,
    max_rel_ci: float = 1.0,
) -> dict[str, Any]:
    rng = np.random.default_rng(random_state)
    n = len(y)

    importances: list[np.ndarray] = []
    signed = True
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        if len(np.unique(y[idx])) < 2:
            continue
        m = clone(model)
        m.fit(X[idx], y[idx])

        if hasattr(m, "coef_"):
            importances.append(np.asarray(m.coef_).ravel())
        elif hasattr(m, "feature_importances_"):
            signed = False
            importances.append(np.asarray(m.feature_importances_))
        else:
            return {
                "supported": False,
                "stable_fraction": float("nan"),
                "reason": (
                    f"{type(model).__name__} exposes neither coef_ nor "
                    "feature_importances_, so bootstrap stability cannot be measured."
                ),
            }

    if not importances:
        return {
            "supported": False,
            "stable_fraction": float("nan"),
            "reason": (
                "Every bootstrap resample was single-class. The positive rate is "
                "too low to resample meaningfully."
            ),
        }

    arr = np.vstack(importances)
    n_features = arr.shape[1]
    ci_lower = np.percentile(arr, 2.5, axis=0)
    ci_upper = np.percentile(arr, 97.5, axis=0)

    result: dict[str, Any] = {
        "supported": True,
        "n_features": n_features,
        "n_bootstraps": int(arr.shape[0]),
        "ci_lower": ci_lower.tolist(),
        "ci_upper": ci_upper.tolist(),
    }

    if signed:
        # Coefficients carry a direction, so a flipped sign is the failure mode.
        sign_consistency = np.zeros(n_features)
        for j in range(n_features):
            col = arr[:, j]
            pos_frac = float((col > 0).mean())
            sign_consistency[j] = max(pos_frac, 1 - pos_frac)
        result["criterion"] = "sign_consistency"
        result["sign_consistency_per_feature"] = sign_consistency.tolist()
        result["stable_fraction"] = float((sign_consistency >= 0.95).mean())
        return result

    # Importances are non-negative, so sign tells us nothing. Measure instead
    # whether each feature's magnitude holds still across resamples.
    means = arr.mean(axis=0)
    ci_width = ci_upper - ci_lower
    scale = np.maximum(means, np.finfo(float).eps)
    rel_ci = ci_width / scale
    # A feature that is consistently negligible is stably unimportant, not unstable.
    negligible = (means <= 1e-12) & (ci_width <= 1e-12)
    stable = negligible | (rel_ci <= max_rel_ci)

    result["criterion"] = "relative_ci_width"
    result["max_rel_ci"] = max_rel_ci
    result["relative_ci_width_per_feature"] = rel_ci.tolist()
    result["stable_fraction"] = float(stable.mean())
    return result


def _calibration_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int) -> float:
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        if i == n_bins - 1:
            mask = (y_prob >= bins[i]) & (y_prob <= bins[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece)


def _feature_label_leakage(
    X: np.ndarray, y: np.ndarray, threshold: float
) -> dict[str, Any]:
    flagged: list[tuple[int, float]] = []
    correlations: list[float] = []
    n_features = X.shape[1]
    n_skipped = 0

    for j in range(n_features):
        col = X[:, j]
        valid = ~np.isnan(col)
        # Compute variance on the finite values only. np.std over a column
        # containing NaN returns NaN, and `NaN == 0` is False, so the original
        # constant-column guard never fired for a column with any NaN in it.
        if valid.sum() < 5 or np.std(col[valid]) == 0 or np.std(y[valid]) == 0:
            n_skipped += 1
            continue
        corr = float(np.corrcoef(col[valid], y[valid])[0, 1])
        if not np.isfinite(corr):
            n_skipped += 1
            continue
        correlations.append(abs(corr))
        if abs(corr) >= threshold:
            flagged.append((j, corr))

    # Filter non-finite values explicitly rather than relying on Python's max().
    # max() over a sequence containing NaN is order-dependent: max([nan, 0.5])
    # returns nan but max([0.5, nan]) returns 0.5, so a single degenerate
    # feature could poison the whole result depending on its column position.
    max_abs_corr = max(correlations) if correlations else 0.0

    return {
        "n_features": n_features,
        "n_skipped_features": n_skipped,
        "threshold": threshold,
        "flagged": flagged,
        "max_abs_corr": float(max_abs_corr),
    }


def _quantize(obj: Any, decimals: int = HASH_DECIMALS) -> Any:
    """Round every float in a nested structure to a fixed precision."""
    if isinstance(obj, float):
        if not np.isfinite(obj):
            return str(obj)
        return round(obj, decimals)
    if isinstance(obj, (np.floating, np.integer)):
        return _quantize(obj.item(), decimals)
    if isinstance(obj, dict):
        return {k: _quantize(v, decimals) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_quantize(v, decimals) for v in obj]
    return obj


def _array_digest(a: np.ndarray, decimals: int | None = HASH_DECIMALS) -> str:
    """Digest an array by content rather than by memory layout.

    ``ndarray.tobytes()`` serialises the buffer as laid out, so the same values
    in Fortran order hash differently from C order, and float noise in the last
    bits changes the digest. Canonicalise both before hashing.
    """
    a = np.ascontiguousarray(a)
    if decimals is not None and np.issubdtype(a.dtype, np.floating):
        a = np.round(a, decimals)
    return hashlib.sha256(a.tobytes() + str(a.dtype).encode() + str(a.shape).encode()).hexdigest()


def _model_fingerprint(model: Any) -> dict[str, str]:
    """Identify the audited model by class and hyperparameters.

    Without this the certificate says nothing about what was audited, and any
    model can be swapped behind a published hash undetected.
    """
    cls = type(model)
    try:
        params = model.get_params(deep=True)
    except Exception:  # not an sklearn estimator
        params = {}
    return {
        "class": f"{cls.__module__}.{cls.__qualname__}",
        "params": json.dumps(_quantize(params), sort_keys=True, default=str),
    }


def _certificate(
    config: AuditConfig,
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    coords: np.ndarray,
    scores: dict[str, Any],
) -> str:
    """Content-addressed hash of the protocol, the model, the data and the result.

    Reproducibility contract: the same protocol version, the same model class
    and hyperparameters, the same data and the same resulting scores produce
    the same hash, on any machine. Scores are quantised before hashing so that
    floating-point drift between BLAS backends does not change the result, and
    arrays are canonicalised so that memory layout does not either.

    What this does NOT cover: fitted weights. Two models of the same class and
    hyperparameters, fitted to the same data, are treated as the same model.
    That is the intended granularity, since the audit refits the model itself.
    """
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "config": _quantize(asdict(config)),
        "model": _model_fingerprint(model),
        "data": {
            "X": _array_digest(X),
            "y": _array_digest(np.asarray(y, dtype=np.int64), decimals=None),
            "coords": _array_digest(coords),
        },
        "scores": _quantize(scores),
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


GATING_TESTS = ("spatial_leakage", "feature_label_leakage")
"""Tests that cap the grade when they fail.

Spatial leakage is the entire reason this protocol exists, and feature-label
leakage means the result is circular. Passing four of five is not a B when the
one failure is either of these. Weighting every test equally would let a model
exhibiting the exact failure the product detects still earn a good grade.
"""


def _grade(passed_count: int, total: int, gating_failed: bool = False) -> str:
    ratio = passed_count / total if total else 0
    if ratio == 1.0:
        grade = "A"
    elif ratio >= 0.8:
        grade = "B"
    elif ratio >= 0.6:
        grade = "C"
    elif ratio >= 0.4:
        grade = "D"
    else:
        grade = "F"

    if gating_failed and grade in ("A", "B", "C"):
        return "D"
    return grade


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def audit(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    coords_xy: np.ndarray,
    feature_names: list[str] | None = None,
    config: AuditConfig | None = None,
) -> AuditResult:
    """Run the full audit protocol.

    Parameters
    ----------
    model : sklearn-compatible binary classifier
        Must implement ``fit`` and ``predict_proba``. Will be cloned per fold;
        the original is not mutated.
    X : ndarray, shape (n_samples, n_features)
        Feature matrix.
    y : ndarray, shape (n_samples,)
        Binary labels (0/1).
    coords_xy : ndarray, shape (n_samples, 2)
        Spatial coordinates for each sample, in **projected metres**
        (e.g. UTM). Used for spatial blocking.
    feature_names : list of str, optional
        Names for diagnostic output. Defaults to ``["f0", "f1", ...]``.
    config : AuditConfig, optional
        Override default thresholds.
    """
    started = time.time()
    cfg = config or AuditConfig()
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y).astype(int)
    coords_xy = np.asarray(coords_xy, dtype=np.float64)
    if feature_names is None:
        feature_names = [f"f{i}" for i in range(X.shape[1])]

    if X.ndim != 2 or X.shape[0] != len(y) or coords_xy.shape != (len(y), 2):
        raise ValueError("X, y, coords_xy shapes are inconsistent")
    if set(np.unique(y).tolist()) - {0, 1}:
        raise ValueError("y must be binary 0/1")
    if len(np.unique(y)) < 2:
        raise ValueError(
            "y contains only one class. An audit needs both positives and negatives."
        )
    if cfg.block_size_km <= 0:
        raise ValueError("block_size_km must be positive")
    if not np.isfinite(coords_xy).all():
        raise ValueError("coords_xy contains non-finite values")

    # Spatial blocking assumes projected metres. Degrees put every point in a
    # single block, which silently degrades spatial CV into no holdout at all
    # and reports a failing score for the wrong reason. Refuse rather than
    # return a confidently wrong grade.
    if not cfg.allow_degree_coords:
        looks_like_degrees = (
            np.abs(coords_xy[:, 0]).max() <= 180.0
            and np.abs(coords_xy[:, 1]).max() <= 90.0
        )
        if looks_like_degrees:
            raise ValueError(
                "coords_xy looks like longitude/latitude degrees, but spatial "
                "blocking requires projected metres (e.g. UTM). Reproject first, "
                "or set allow_degree_coords=True if this is genuinely a metric "
                "grid within these bounds."
            )

    prior = float(y.mean())
    logger.info("Audit start: n=%d, positives=%d, prior=%.3f", len(y), y.sum(), prior)

    # Test 1+2: random vs spatial CV
    pr_random = _random_cv_score(model, X, y, cfg.n_random_folds, cfg.random_state)
    block_ids = _spatial_blocks(coords_xy, cfg.block_size_km)
    pr_spatial = _spatial_cv_score(model, X, y, block_ids, cfg.n_spatial_folds)
    gap = pr_random - pr_spatial if not (np.isnan(pr_random) or np.isnan(pr_spatial)) else float("nan")

    leakage_test = TestResult(
        name="spatial_leakage",
        passed=bool(not np.isnan(gap) and gap <= cfg.spatial_leakage_max_gap),
        score=float(gap),
        threshold=cfg.spatial_leakage_max_gap,
        detail={
            "pr_auc_random_cv": pr_random,
            "pr_auc_spatial_cv": pr_spatial,
            "n_spatial_blocks": int(len(np.unique(block_ids))),
            "block_size_km": cfg.block_size_km,
        },
    )

    baseline_test = TestResult(
        name="beats_class_prior",
        passed=bool(not np.isnan(pr_spatial) and pr_spatial > prior),
        score=float(pr_spatial - prior) if not np.isnan(pr_spatial) else float("nan"),
        threshold=0.0,
        detail={"pr_auc_spatial_cv": pr_spatial, "class_prior": prior},
    )

    # Test 3: bootstrap stability
    boot = _bootstrap_stability(
        model, X, y, cfg.n_bootstrap, cfg.random_state,
        max_rel_ci=cfg.unsigned_importance_max_rel_ci,
    )
    bootstrap_test = TestResult(
        name="bootstrap_stability",
        passed=bool(boot.get("supported") and boot["stable_fraction"] >= 0.5),
        score=float(boot.get("stable_fraction", float("nan"))),
        threshold=0.5,
        detail=boot,
    )

    # Test 4: calibration -- fit on all data, evaluate on a holdout fold
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=cfg.random_state)
    train_idx, test_idx = next(iter(skf.split(X, y)))
    cal_model = clone(model)
    cal_model.fit(X[train_idx], y[train_idx])
    cal_probs = cal_model.predict_proba(X[test_idx])[:, 1]
    ece = _calibration_ece(y[test_idx], cal_probs, cfg.calibration_n_bins)
    calibration_test = TestResult(
        name="calibration",
        passed=ece <= cfg.calibration_max_ece,
        score=float(ece),
        threshold=cfg.calibration_max_ece,
        detail={"expected_calibration_error": ece, "n_bins": cfg.calibration_n_bins},
    )

    # Test 5: feature-label leakage
    leak = _feature_label_leakage(X, y, cfg.feature_leakage_threshold)
    feature_leakage_test = TestResult(
        name="feature_label_leakage",
        passed=len(leak["flagged"]) == 0,
        score=float(leak["max_abs_corr"]),
        threshold=cfg.feature_leakage_threshold,
        detail={
            "flagged_features": [
                {"name": feature_names[j], "index": j, "correlation": c}
                for j, c in leak["flagged"]
            ],
            "max_abs_corr": leak["max_abs_corr"],
        },
    )

    tests = [
        leakage_test,
        baseline_test,
        bootstrap_test,
        calibration_test,
        feature_leakage_test,
    ]
    passed_count = sum(1 for t in tests if t.passed)
    gating_failed = any(t.name in GATING_TESTS and not t.passed for t in tests)
    grade = _grade(passed_count, len(tests), gating_failed=gating_failed)

    summary = {
        "n_samples": int(len(y)),
        "n_features": int(X.shape[1]),
        "n_positives": int(y.sum()),
        "class_prior": prior,
        "pr_auc_random_cv": pr_random,
        "pr_auc_spatial_cv": pr_spatial,
        "spatial_leakage_gap": gap,
        "tests_passed": passed_count,
        "tests_total": len(tests),
        "grade": grade,
        "gating_test_failed": gating_failed,
        "protocol_version": PROTOCOL_VERSION,
    }

    cert = _certificate(cfg, model, X, y, coords_xy, summary)

    elapsed = time.time() - started
    logger.info(
        "Audit complete in %.1fs: grade=%s, passed=%d/%d, cert=%s",
        elapsed, grade, passed_count, len(tests), cert[:12],
    )

    return AuditResult(
        passed=passed_count == len(tests),
        grade=grade,
        tests=tests,
        summary=summary,
        certificate=cert,
        elapsed_seconds=elapsed,
    )
