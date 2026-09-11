# GeoMine Benchmark

This document carries two separate claims. They are kept separate on purpose,
because conflating them is the mistake this document made in an earlier
draft -- see [CLAIMS_AUDIT.md](CLAIMS_AUDIT.md) for the full account.

1. **The audit protocol benchmark** -- proof that `geomine.audit` runs end to
   end on real data and produces a certificate anyone can reproduce. This is
   real, working, and verifiable today.
2. **The Phase 2 targeting result (PR-AUC 0.453)** -- an early research
   result on the mineral-prospectivity model. It is not yet certified by the
   audit protocol and not yet independently reproducible. Read its caveats
   before quoting it.

---

## 1. The Audit Protocol Benchmark (verifiable today)

| Metric | Score |
|---|---|
| PR-AUC, random CV (5-fold) | 0.153 |
| PR-AUC, spatial block CV (25km blocks) | 0.144 |
| Spatial leakage gap | 0.009 |
| Class prior baseline | 0.124 |
| Tests passed | 5/5 |
| Grade | A |

**Certificate:** `c8bd3fd20d7f29186f447ce05942ead8083495a70787f75365ad37767ed2100b`

**What this is.** A logistic regression over two features -- distance to the
nearest mapped intrusive-igneous unit, and distance to the nearest digitised
regional fault -- against the 17 real, named Great Dyke deposits already
committed to this repository (`data/training/deposits.geojson`), plus
randomly sampled background points. Both features come from real, committed
geology data (`data/geology/`), not satellite imagery.

**What this is not.** It is not a claim that these two features are good
predictors of mineral deposits -- notice the scores are modest and only
narrowly beat the class prior, which is the honest result of a simple,
disclosed feature set. **The point of this benchmark is not the score. It is
that the score is real and reproducible**, which is the product's entire
premise.

**How to verify:**

```bash
pip install -e ".[api,audit]"
geomine audit benchmark/dataset.parquet benchmark/model.joblib \
    --block-size-km 25.0 \
    --output your_audit.md \
    --json-output your_audit.json
```

Compare the `certificate` field in your output to the one published above.
They will match, on any machine, because the certificate hashes the
protocol version, the model's class and parameters, the data, and the
quantised result -- not raw floating-point output that drifts between BLAS
backends. See `geomine/audit/core.py` for exactly what goes into the hash.

To regenerate the benchmark artifacts from scratch (deterministic --
re-running this reproduces the same certificate):

```bash
geomine build-benchmark
```

---

## 2. The Phase 2 Targeting Result (research result, not yet audited)

| Metric | Score |
|---|---|
| PR-AUC, random CV (5-fold) | 0.612 |
| PR-AUC, leave-one-tile-out CV | 0.453 |
| Spatial leakage gap | 0.159 |

**Geographic extent:** Great Dyke, Zimbabwe -- 4 Sentinel-2 tiles (T35KRU, T36KTC/D/E)
**Deposits:** 17 labelled (Cr, PGM, Ni, Au)
**Model:** an ImageNet-pretrained ViT-Small with a six-band input adapter
(`scripts/run_prithvi_loto.py`) -- **not** Prithvi-EO-2.0. Earlier drafts of
this project's materials named Prithvi; that was inaccurate and is corrected
here. Prithvi integration remains a possible future direction, not something
already built.

**Status, stated plainly:**

- This model has not been run through `geomine.audit`. It cannot be yet: the
  protocol clones and refits an sklearn-compatible classifier per fold, and
  this model is a PyTorch module with neither `predict_proba` nor
  `coef_`/`feature_importances_`. A prior version of this document listed
  "Bootstrap stable feature fraction 0.83" and "Tests passed 5/5, Grade A"
  for this model. Those figures could not have come from this protocol
  against this model, and have been removed rather than left unverified.
- The training script that produced 0.453 sets no random seed for PyTorch,
  numpy, or the data loader shuffle. Re-running it is not currently
  guaranteed to reproduce the same number.
- No confidence interval has been computed. With 17 positives spread across
  four cross-validation folds, the honest interval around 0.453 is wide
  enough that it likely overlaps the Phase 1 result (0.228) this project
  itself called a failure. Treat 0.453 as evidence that cross-tile signal
  exists, not as a precise, stable performance figure.

None of this means the result is worthless -- it is a real improvement in
kind over Phase 1's collapse, and the honest fix is to seed the training run,
report a range instead of a point estimate, and either wrap the model for
the audit protocol or build a comparable audit for foundation models. That
work is tracked, not yet done. See [LAUNCH_PLAN.md](LAUNCH_PLAN.md).

## Why the Random-vs-Spatial Gap Matters

Most mining-AI benchmarks report only random-CV PR-AUC, which inflates by
capturing spatial autocorrelation between nearby positives. Spatial CV holds
out entire regions, forcing a model to predict on geography it has not seen.

Phase 1 random CV was 0.841. Its leave-one-tile-out CV was 0.228 -- a 0.613
gap, and the failure that started this project's pivot. That comparison is
documented in [PHASE1_POSTMORTEM.md](PHASE1_POSTMORTEM.md) and
[STATUS.md](STATUS.md) and is accurate as recorded there.

## Audit Protocol (`geomine.audit`)

Every audit run executes five tests:

1. **Spatial leakage** -- gap between random CV and spatial block CV must be < 0.30. Failing this caps the grade regardless of the other four.
2. **Class prior** -- spatial CV PR-AUC must exceed the rate of positives in the dataset.
3. **Bootstrap stability** -- for linear models, coefficient signs must hold across resamples; for tree ensembles, whose importances are non-negative by construction, the importance-weighted magnitude must hold instead.
4. **Calibration** -- expected calibration error on a held-out fold must be < 0.10.
5. **Feature-label leakage** -- no feature with |correlation| >= 0.95 against the label. Failing this also caps the grade.

Failing any test fails the audit; failing test 1 or test 5 caps the grade at D regardless of the other three, because those two are the failure modes the protocol exists to catch. The protocol is published in `geomine/audit/core.py`; the thresholds are public and can be overridden per engagement via `AuditConfig`.

## What This Number Is Not

- **Not a guarantee of mineral discovery.** PR-AUC measures rank quality on labelled deposits, not exploration outcome.
- **Not transferable to other geologies.** Any model here was trained on the Great Dyke. A different orogen needs a different model and a different audit.
- **Not a substitute for fieldwork.** Probability maps narrow targets; drilling confirms them.

---

*Run the audit yourself. Match the hash. The number is what it claims to be -- and where it isn't yet, this document says so.*
