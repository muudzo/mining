"""Tests for geomine.audit.report -- the customer-facing markdown/JSON output."""
from __future__ import annotations

import math

from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier

from geomine.audit import AuditConfig, audit
from geomine.audit.report import _fmt, to_json, to_markdown


def test_fmt_renders_nan_as_explanatory_text_not_literal_nan():
    assert _fmt(float("nan")) != "nan"
    assert "N/A" in _fmt(float("nan"))


def test_fmt_renders_normal_floats_unchanged():
    assert _fmt(0.4567, ".3f") == "0.457"


def test_markdown_report_never_prints_bare_nan(clean_dataset):
    """A model unsupported for bootstrap stability produces a NaN score.
    Before the report formatter was fixed, this printed the literal string
    "nan" into a customer-facing document with no explanation.
    """
    result = audit(
        KNeighborsClassifier(n_neighbors=3),
        clean_dataset["X"], clean_dataset["y"], clean_dataset["coords"],
        config=AuditConfig(n_bootstrap=10, block_size_km=40),
    )
    md = to_markdown(result, model_name="knn-demo")
    assert "| nan |" not in md
    assert " nan " not in f" {md} "
    assert "N/A" in md  # the bootstrap_stability row should show this


def test_json_report_round_trips(clean_dataset):
    result = audit(
        LogisticRegression(max_iter=1000),
        clean_dataset["X"], clean_dataset["y"], clean_dataset["coords"],
        config=AuditConfig(n_bootstrap=10, block_size_km=40),
    )
    payload = to_json(result)
    assert result.certificate in payload
    assert result.grade in payload
