# GeoMine Audit Report: great-dyke-demo

**Grade:** A  (5/5 tests passed)
**Certificate:** `c8bd3fd20d7f29186f447ce05942ead8083495a70787f75365ad37767ed2100b`
**Protocol version:** v1
**Elapsed:** 0.7s

## Dataset

- Samples: 137
- Features: 2
- Positives: 17 (prior = 0.124)

## Headline Numbers

- PR-AUC (random CV):  **0.153**
- PR-AUC (spatial CV): **0.144**
- Spatial leakage gap: **0.009**

## Tests

| Test | Result | Score | Threshold |
|---|---|---|---|
| spatial_leakage | PASS | 0.009 | 0.300 |
| beats_class_prior | PASS | 0.020 | 0.000 |
| bootstrap_stability | PASS | 0.500 | 0.500 |
| calibration | PASS | 0.059 | 0.100 |
| feature_label_leakage | PASS | 0.147 | 0.950 |

## Test Details

### spatial_leakage -- PASS

- Score: 0.009 (threshold: 0.300)
- Details:
    - pr_auc_random_cv: 0.1528833137897628
    - pr_auc_spatial_cv: 0.1441291184393969
    - n_spatial_blocks: 65
    - block_size_km: 25.0

### beats_class_prior -- PASS

- Score: 0.020 (threshold: 0.000)
- Details:
    - pr_auc_spatial_cv: 0.1441291184393969
    - class_prior: 0.12408759124087591

### bootstrap_stability -- PASS

- Score: 0.500 (threshold: 0.500)
- Details:
    - supported: True
    - n_features: 2
    - n_bootstraps: 200
    - ci_lower: [-0.12955367507480578, -0.0036129266126995645]
    - ci_upper: [-0.010862355936054089, 0.012077876192396628]
    - criterion: sign_consistency
    - sign_consistency_per_feature: [1.0, 0.81]
    - stable_fraction: 0.5

### calibration -- PASS

- Score: 0.059 (threshold: 0.100)
- Details:
    - expected_calibration_error: 0.059031704167466864
    - n_bins: 10

### feature_label_leakage -- PASS

- Score: 0.147 (threshold: 0.950)
- Details:
    - flagged_features: []
    - max_abs_corr: 0.14728015198184657

---

*Audit run by `geomine.audit` protocol v1. The certificate covers the protocol version, the model's class and hyperparameters, the dataset, and the resulting scores. Independent verifiers can re-derive it from the same inputs on a different machine.*