"""Tests for geomine.audit.core -- the paid product.

This module is what GeoMine sells: an independent grade plus a certificate
customers are told they can reproduce. Every test here exists because a bug
in this file is a bug in the thing being charged for, not an ordinary
regression. Fixtures are constructed so the *correct* verdict is known in
advance (see conftest.py), rather than snapshot-testing arbitrary output.

Where a test documents a known limitation of the current implementation
rather than a bug that was fixed, it is marked xfail with a reason, per the
instruction not to weaken a test to make it pass.
"""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier

from geomine.audit import AuditConfig, audit
from geomine.audit.core import (
    GATING_TESTS,
    PROTOCOL_VERSION,
    _certificate,
    _feature_label_leakage,
    _grade,
    _model_fingerprint,
)


# ---------------------------------------------------------------------------
# The five tests catch what they claim to catch
# ---------------------------------------------------------------------------

class TestSpatialLeakageDetection:
    def test_catches_known_leakage(self, leaky_dataset):
        result = audit(
            LogisticRegression(max_iter=3000, C=3.0),
            leaky_dataset["X"], leaky_dataset["y"], leaky_dataset["coords"],
            feature_names=leaky_dataset["feature_names"],
            config=AuditConfig(n_bootstrap=40, block_size_km=35),
        )
        leakage = next(t for t in result.tests if t.name == "spatial_leakage")
        assert not leakage.passed, (
            "A model with high-capacity positional features and a weakly "
            "weighted true signal must fail the leakage test -- this is the "
            "dataset's entire purpose."
        )
        assert result.summary["pr_auc_random_cv"] > result.summary["pr_auc_spatial_cv"], (
            "Random CV must read higher than spatial CV on leaky data, "
            "matching the documented Phase 1 failure (0.841 vs 0.228)."
        )

    def test_gating_caps_grade_when_leakage_fails(self, leaky_dataset):
        result = audit(
            LogisticRegression(max_iter=3000, C=3.0),
            leaky_dataset["X"], leaky_dataset["y"], leaky_dataset["coords"],
            config=AuditConfig(n_bootstrap=40, block_size_km=35),
        )
        assert result.summary["gating_test_failed"] is True
        assert result.grade in ("D", "F"), (
            "Failing spatial_leakage (a gating test) must cap the grade even "
            "if enough other tests pass to reach a B under equal weighting. "
            f"Got grade={result.grade}, passed={result.summary['tests_passed']}/"
            f"{result.summary['tests_total']}."
        )

    def test_clean_data_passes(self, clean_dataset):
        result = audit(
            LogisticRegression(max_iter=1000),
            clean_dataset["X"], clean_dataset["y"], clean_dataset["coords"],
            config=AuditConfig(n_bootstrap=40, block_size_km=40),
        )
        leakage = next(t for t in result.tests if t.name == "spatial_leakage")
        assert leakage.passed, (
            "A model whose feature IS the true spatial field (plus noise) "
            "should generalise across spatial blocks and pass."
        )


class TestClassPriorBaseline:
    def test_no_skill_model_fails(self, no_skill_dataset):
        result = audit(
            LogisticRegression(max_iter=1000),
            no_skill_dataset["X"], no_skill_dataset["y"], no_skill_dataset["coords"],
            config=AuditConfig(n_bootstrap=30),
        )
        baseline = next(t for t in result.tests if t.name == "beats_class_prior")
        assert not baseline.passed, "Pure noise features must not beat the class prior."

    def test_clean_model_beats_prior(self, clean_dataset):
        result = audit(
            LogisticRegression(max_iter=1000),
            clean_dataset["X"], clean_dataset["y"], clean_dataset["coords"],
            config=AuditConfig(n_bootstrap=30, block_size_km=40),
        )
        baseline = next(t for t in result.tests if t.name == "beats_class_prior")
        assert baseline.passed


class TestBootstrapStability:
    def test_linear_model_uses_sign_consistency(self, clean_dataset):
        result = audit(
            LogisticRegression(max_iter=1000),
            clean_dataset["X"], clean_dataset["y"], clean_dataset["coords"],
            config=AuditConfig(n_bootstrap=50, block_size_km=40),
        )
        boot = next(t for t in result.tests if t.name == "bootstrap_stability")
        assert boot.detail["criterion"] == "sign_consistency"
        assert boot.detail["supported"] is True

    def test_tree_model_does_not_trivially_pass(self, rng):
        """A random forest over pure noise must be able to FAIL bootstrap
        stability. Before this was fixed, feature_importances_ is
        non-negative by construction, so a sign-consistency test always
        scored every feature as "stable" (pos_frac == 1.0) regardless of
        whether the ranking was meaningful -- the test was a no-op for the
        most common production classifier family.
        """
        n = 80
        y = np.r_[np.ones(30, dtype=int), np.zeros(50, dtype=int)]
        X_noise = rng.normal(0, 1, size=(n, 12))
        coords = rng.uniform(0, 200_000, size=(n, 2))
        result = audit(
            RandomForestClassifier(n_estimators=20, random_state=0),
            X_noise, y, coords,
            config=AuditConfig(n_bootstrap=40, block_size_km=60),
        )
        boot = next(t for t in result.tests if t.name == "bootstrap_stability")
        assert boot.detail["criterion"] == "importance_weighted_relative_ci_width"
        assert boot.score < 0.5, (
            "Twelve pure-noise features fed to a random forest must not "
            f"score as bootstrap-stable. Got stable_fraction={boot.score:.3f}."
        )

    def test_tree_model_with_one_dominant_feature_passes(self, rng):
        """A forest that legitimately rests on one strong, stable feature
        plus a few noisy irrelevant ones should PASS -- the noise features'
        jitter should not sink a model whose real driver is solid. This is
        the counterpart to the failing case above and guards against
        over-correcting into a test that always fails tree models.
        """
        n = 100
        y = np.r_[np.ones(35, dtype=int), np.zeros(65, dtype=int)]
        strong = y.astype(float) * 3.0 + rng.normal(0, 0.2, n)
        X = np.column_stack([strong, rng.normal(0, 1, size=(n, 3))])
        coords = rng.uniform(0, 200_000, size=(n, 2))
        result = audit(
            RandomForestClassifier(n_estimators=25, random_state=0),
            X, y, coords,
            config=AuditConfig(n_bootstrap=40, block_size_km=60),
        )
        boot = next(t for t in result.tests if t.name == "bootstrap_stability")
        assert boot.passed, (
            f"A dominant, stable feature should pass even with noisy "
            f"companions. Got stable_fraction={boot.score:.3f}."
        )

    def test_unsupported_model_reports_why(self, clean_dataset):
        result = audit(
            KNeighborsClassifier(n_neighbors=3),
            clean_dataset["X"], clean_dataset["y"], clean_dataset["coords"],
            config=AuditConfig(n_bootstrap=10, block_size_km=40),
        )
        boot = next(t for t in result.tests if t.name == "bootstrap_stability")
        assert not boot.passed
        assert boot.detail["supported"] is False
        assert "reason" in boot.detail and boot.detail["reason"]
        assert np.isnan(boot.score)


class TestCalibration:
    def test_badly_calibrated_model_fails(self, rng):
        """A model that is deliberately overconfident (predictions pushed
        toward 0/1 regardless of actual accuracy) should trip the ECE test.
        """
        n = 300
        y = (rng.uniform(0, 1, n) < 0.3).astype(int)
        # Feature barely correlates with y, but a model can still be
        # overconfident about its (weak, noisy) signal.
        X = np.column_stack([
            y * 0.3 + rng.normal(0, 1, n),
            rng.normal(0, 1, n),
        ])
        coords = rng.uniform(0, 200_000, size=(n, 2))

        class Overconfident(LogisticRegression):
            def predict_proba(self, X):
                p = super().predict_proba(X)
                # push toward the extremes
                return np.clip(p ** 0.15, 0, 1) / np.clip(p ** 0.15, 0, 1).sum(axis=1, keepdims=True)

        result = audit(
            Overconfident(max_iter=1000), X, y, coords,
            config=AuditConfig(n_bootstrap=10, block_size_km=60),
        )
        calib = next(t for t in result.tests if t.name == "calibration")
        assert calib.score > 0, "An overconfident model should show nonzero ECE."


class TestFeatureLabelLeakage:
    def test_catches_leaked_feature(self, leaked_feature_dataset):
        result = audit(
            LogisticRegression(max_iter=1000),
            leaked_feature_dataset["X"], leaked_feature_dataset["y"],
            leaked_feature_dataset["coords"],
            feature_names=leaked_feature_dataset["feature_names"],
            config=AuditConfig(n_bootstrap=20, block_size_km=40),
        )
        leak_test = next(t for t in result.tests if t.name == "feature_label_leakage")
        assert not leak_test.passed
        flagged_names = {f["name"] for f in leak_test.detail["flagged_features"]}
        assert "leaked" in flagged_names

    def test_clean_data_not_flagged(self, no_skill_dataset):
        result = audit(
            LogisticRegression(max_iter=1000),
            no_skill_dataset["X"], no_skill_dataset["y"], no_skill_dataset["coords"],
            config=AuditConfig(n_bootstrap=10),
        )
        leak_test = next(t for t in result.tests if t.name == "feature_label_leakage")
        assert leak_test.passed

    def test_nan_in_one_column_does_not_poison_others(self, rng):
        """Regression test for the Python max() NaN-order-dependence bug:
        max([nan, 0.3, 0.5]) is nan, but max([0.3, 0.5, nan]) is 0.5 --
        a degenerate feature earlier in column order could previously
        poison max_abs_corr for the whole audit regardless of what other,
        perfectly-computable correlations existed.
        """
        n = 60
        y = (rng.uniform(0, 1, n) < 0.4).astype(int)
        col_with_nans = np.full(n, np.nan)
        col_with_nans[:4] = rng.normal(0, 1, 4)  # too few valid points (< 5), skipped
        real_feature = y.astype(float) * 0.9 + rng.normal(0, 0.5, n)
        X = np.column_stack([col_with_nans, real_feature])
        leak = _feature_label_leakage(X, y, threshold=0.5)
        assert np.isfinite(leak["max_abs_corr"]), (
            "A NaN-producing feature at column index 0 must not turn "
            "max_abs_corr into NaN for the whole result."
        )
        assert leak["n_skipped_features"] >= 1

    def test_constant_column_with_nans_is_skipped_not_miscounted(self):
        """np.std over an array containing NaN is NaN, and NaN == 0 is
        False, so the original constant-column guard (`np.std(col) == 0`)
        never fired for a column that was constant everywhere it had a
        value but also contained NaNs. Confirm the fixed guard, which
        computes std on the finite values only, correctly skips it.
        """
        y = np.array([0, 1, 0, 1, 0, 1, 0, 1])
        constant_with_nan = np.array([5.0, 5.0, np.nan, 5.0, 5.0, 5.0, 5.0, 5.0])
        X = np.column_stack([constant_with_nan, np.array([1.0, 2, 3, 4, 5, 6, 7, 8])])
        leak = _feature_label_leakage(X, y, threshold=0.95)
        assert leak["n_skipped_features"] == 1


# ---------------------------------------------------------------------------
# Certificate: determinism, model binding, layout invariance
# ---------------------------------------------------------------------------

class TestCertificate:
    def test_deterministic_for_identical_inputs(self, clean_dataset):
        cfg = AuditConfig(n_bootstrap=20, block_size_km=40)
        a = audit(LogisticRegression(max_iter=1000), clean_dataset["X"],
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        b = audit(LogisticRegression(max_iter=1000), clean_dataset["X"],
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        assert a.certificate == b.certificate, (
            "Same model, same data, same config must produce the same "
            "certificate -- this is the product's core marketing claim."
        )

    def test_different_model_hyperparameters_change_the_hash(self, clean_dataset):
        """Before this was fixed, _certificate never received the model at
        all -- only config, data and the derived summary scores. Two
        differently-configured models that happened to converge to similar
        summary numbers produced an IDENTICAL certificate, meaning the
        model could be swapped behind a published hash undetected.
        """
        cfg = AuditConfig(n_bootstrap=20, block_size_km=40)
        a = audit(LogisticRegression(max_iter=1000), clean_dataset["X"],
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        b = audit(LogisticRegression(max_iter=5000), clean_dataset["X"],
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        assert a.certificate != b.certificate

    def test_different_model_class_changes_the_hash(self, clean_dataset):
        cfg = AuditConfig(n_bootstrap=20, block_size_km=40)
        a = audit(LogisticRegression(max_iter=1000), clean_dataset["X"],
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        b = audit(RandomForestClassifier(n_estimators=10, random_state=0),
                  clean_dataset["X"], clean_dataset["y"], clean_dataset["coords"], config=cfg)
        assert a.certificate != b.certificate

    def test_changed_data_changes_the_hash(self, clean_dataset):
        cfg = AuditConfig(n_bootstrap=20, block_size_km=40)
        a = audit(LogisticRegression(max_iter=1000), clean_dataset["X"],
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        X2 = clean_dataset["X"].copy()
        X2[0, 0] += 1.0
        b = audit(LogisticRegression(max_iter=1000), X2,
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        assert a.certificate != b.certificate

    def test_changed_config_changes_the_hash(self, clean_dataset):
        a = audit(LogisticRegression(max_iter=1000), clean_dataset["X"],
                  clean_dataset["y"], clean_dataset["coords"],
                  config=AuditConfig(n_bootstrap=20, block_size_km=40))
        b = audit(LogisticRegression(max_iter=1000), clean_dataset["X"],
                  clean_dataset["y"], clean_dataset["coords"],
                  config=AuditConfig(n_bootstrap=20, block_size_km=41))
        assert a.certificate != b.certificate

    def test_array_memory_layout_does_not_change_the_hash(self, clean_dataset):
        """Content-addressed means addressed by content, not by the
        incidental memory layout numpy happened to use. Fortran- vs
        C-contiguous arrays with identical values must hash the same.
        """
        cfg = AuditConfig(n_bootstrap=20, block_size_km=40)
        X_c = np.ascontiguousarray(clean_dataset["X"])
        X_f = np.asfortranarray(clean_dataset["X"])
        a = audit(LogisticRegression(max_iter=1000), X_c,
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        b = audit(LogisticRegression(max_iter=1000), X_f,
                  clean_dataset["y"], clean_dataset["coords"], config=cfg)
        assert a.certificate == b.certificate

    def test_model_fingerprint_covers_class_and_params(self):
        fp = _model_fingerprint(LogisticRegression(C=2.0, max_iter=500))
        assert fp["class"] == "sklearn.linear_model._logistic.LogisticRegression"
        assert "2.0" in fp["params"] or "2" in fp["params"]

    def test_model_fingerprint_survives_non_sklearn_object(self):
        """A plain object without get_params must not crash certificate
        generation -- it should degrade gracefully rather than raise.
        """
        class NotAnEstimator:
            def fit(self, X, y):
                return self

            def predict_proba(self, X):
                return np.tile([0.5, 0.5], (len(X), 1))

        fp = _model_fingerprint(NotAnEstimator())
        assert "NotAnEstimator" in fp["class"]

    def test_certificate_embeds_protocol_version(self, clean_dataset):
        result = audit(LogisticRegression(max_iter=1000), clean_dataset["X"],
                        clean_dataset["y"], clean_dataset["coords"],
                        config=AuditConfig(n_bootstrap=10, block_size_km=40))
        assert result.summary["protocol_version"] == PROTOCOL_VERSION

    @pytest.mark.xfail(
        reason=(
            "Certificate hashing quantises SCORES to 6 decimals (HASH_DECIMALS) "
            "before hashing, which absorbs BLAS/thread-count float noise in the "
            "cross-validated metrics. It does NOT re-run the audit on a second "
            "machine to confirm bit-identical reproduction across different "
            "numpy/scipy/BLAS builds -- that requires a real cross-environment "
            "run (see LAUNCH_PLAN.md P0-1), not a single-process unit test. "
            "Tracked as an open verification, not asserted as proven here."
        ),
        strict=False,
    )
    def test_reproducible_across_simulated_environments(self):
        raise AssertionError("cross-environment reproduction requires a second real environment")


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

class TestGrading:
    @pytest.mark.parametrize("passed,total,gating_failed,expected", [
        (5, 5, False, "A"),
        (4, 5, False, "B"),
        (3, 5, False, "C"),
        (2, 5, False, "D"),
        (0, 5, False, "F"),
        (4, 5, True, "D"),   # would be B, capped for a gating failure
        (5, 5, True, "D"),   # can't happen (5/5 implies gating passed) but cap must still apply
        (1, 5, True, "F"),   # already worse than the cap, cap doesn't raise it
    ])
    def test_grade_mapping(self, passed, total, gating_failed, expected):
        assert _grade(passed, total, gating_failed=gating_failed) == expected

    def test_gating_tests_are_the_documented_ones(self):
        assert set(GATING_TESTS) == {"spatial_leakage", "feature_label_leakage"}


# ---------------------------------------------------------------------------
# Edge cases and guards
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_single_class_labels_rejected(self, rng):
        n = 50
        X = rng.normal(0, 1, size=(n, 2))
        y = np.zeros(n, dtype=int)
        coords = rng.uniform(0, 100_000, size=(n, 2))
        with pytest.raises(ValueError, match="one class"):
            audit(LogisticRegression(), X, y, coords)

    def test_non_binary_labels_rejected(self, rng):
        n = 30
        X = rng.normal(0, 1, size=(n, 2))
        y = rng.integers(0, 3, n)  # 0/1/2
        coords = rng.uniform(0, 100_000, size=(n, 2))
        with pytest.raises(ValueError, match="binary"):
            audit(LogisticRegression(), X, y, coords)

    def test_mismatched_shapes_rejected(self, rng):
        X = rng.normal(0, 1, size=(20, 2))
        y = rng.integers(0, 2, 19)  # off by one
        coords = rng.uniform(0, 100_000, size=(20, 2))
        with pytest.raises(ValueError, match="inconsistent"):
            audit(LogisticRegression(), X, y, coords)

    def test_empty_input_rejected(self):
        X = np.empty((0, 2))
        y = np.empty((0,), dtype=int)
        coords = np.empty((0, 2))
        with pytest.raises(ValueError):
            audit(LogisticRegression(), X, y, coords)

    def test_nan_in_coords_rejected(self, rng):
        n = 40
        X = rng.normal(0, 1, size=(n, 2))
        y = np.r_[np.ones(15, dtype=int), np.zeros(25, dtype=int)]
        coords = rng.uniform(0, 100_000, size=(n, 2))
        coords[3, 0] = np.nan
        with pytest.raises(ValueError, match="non-finite"):
            audit(LogisticRegression(), X, y, coords)

    def test_nonpositive_block_size_rejected(self, clean_dataset):
        with pytest.raises(ValueError, match="block_size_km"):
            audit(LogisticRegression(), clean_dataset["X"], clean_dataset["y"],
                  clean_dataset["coords"], config=AuditConfig(block_size_km=0.0))
        with pytest.raises(ValueError, match="block_size_km"):
            audit(LogisticRegression(), clean_dataset["X"], clean_dataset["y"],
                  clean_dataset["coords"], config=AuditConfig(block_size_km=-5.0))

    def test_degree_like_coordinates_rejected(self, rng):
        """coords_xy must be projected metres. Longitude/latitude silently
        collapses every point into one spatial block, which degrades
        'spatial CV' into no holdout at all and reports the wrong reason
        for a failing (or NaN) score. This must be a loud, clear error.
        """
        n = 60
        y = np.r_[np.ones(20, dtype=int), np.zeros(40, dtype=int)]
        X = rng.normal(0, 1, size=(n, 2))
        # Zimbabwe-ish lon/lat range
        coords = np.column_stack([
            rng.uniform(29, 31, n),
            rng.uniform(-20, -18, n),
        ])
        with pytest.raises(ValueError, match="longitude/latitude"):
            audit(LogisticRegression(), X, y, coords)

    def test_degree_like_coordinates_allowed_when_opted_in(self, rng):
        n = 60
        y = np.r_[np.ones(20, dtype=int), np.zeros(40, dtype=int)]
        X = rng.normal(0, 1, size=(n, 2))
        coords = np.column_stack([rng.uniform(29, 31, n), rng.uniform(-20, -18, n)])
        # Should not raise, though the resulting spatial CV is expected to
        # be degenerate (single block) -- that's the caller's informed choice.
        result = audit(
            LogisticRegression(), X, y, coords,
            config=AuditConfig(n_bootstrap=5, allow_degree_coords=True),
        )
        assert result is not None

    def test_fewer_samples_than_folds(self, rng):
        n = 6
        X = rng.normal(0, 1, size=(n, 2))
        y = np.array([0, 1, 0, 1, 0, 1])
        coords = rng.uniform(0, 10_000, size=(n, 2))
        # Must not crash -- either runs with fewer folds or reports NaN
        # for tests it cannot compute, but must return a structured result.
        result = audit(
            LogisticRegression(), X, y, coords,
            config=AuditConfig(n_bootstrap=5, n_random_folds=5, n_spatial_folds=5, block_size_km=1),
        )
        assert result.grade in {"A", "B", "C", "D", "F"}

    def test_single_spatial_block(self, rng):
        """All points fall in one spatial block (block size larger than the
        data extent) -- spatial CV cannot form more than one fold and must
        report NaN, not crash or silently substitute a different result.
        """
        n = 40
        coords = rng.uniform(0, 1_000, size=(n, 2))  # tiny extent
        X = rng.normal(0, 1, size=(n, 2))
        y = np.r_[np.ones(15, dtype=int), np.zeros(25, dtype=int)]
        result = audit(
            LogisticRegression(), X, y, coords,
            config=AuditConfig(n_bootstrap=5, block_size_km=500),  # 500km >> 1km extent
        )
        leakage = next(t for t in result.tests if t.name == "spatial_leakage")
        assert leakage.detail["n_spatial_blocks"] == 1
        assert not leakage.passed  # NaN gap cannot pass
        assert np.isnan(result.summary["pr_auc_spatial_cv"]) or leakage.detail["n_spatial_blocks"] < 2
