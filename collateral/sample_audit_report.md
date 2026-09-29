# SAMPLE — GeoMine Audit Report

> **This is a sample.** It shows what an audit engagement delivers, using GeoMine's own public
> benchmark as the "customer" dataset and model. Every number below comes from running
> `geomine audit` on the files in [`benchmark/`](../benchmark/). Nothing is illustrative
> except the sections marked *Reviewer's reading*, which show the kind of plain-language
> interpretation a person writes for each engagement.

---

## 1. What was audited

| | |
|---|---|
| Model | Logistic regression on two features: distance to intrusive contact (km), distance to mapped fault (km) |
| Dataset | 137 locations on the Great Dyke, Zimbabwe: 17 real named Cr/PGM deposits and 120 sampled background points |
| Class prior | 0.124 (17 / 137) |
| Spatial block size | 25 km |
| Protocol | GeoMine audit protocol v1 ([`geomine/audit/core.py`](../geomine/audit/core.py)) |

## 2. Result

**Grade: A — 5 of 5 tests passed.**

**Certificate:** `c8bd3fd20d7f29186f447ce05942ead8083495a70787f75365ad37767ed2100b`

| Test | Result | Score | Threshold | What it checks |
|---|---|---|---|---|
| Spatial leakage | PASS | 0.009 | < 0.300 | Does the score collapse when nearby points can't leak between train and test? |
| Beats class prior | PASS | 0.020 | > 0.000 | Is spatial-CV PR-AUC better than picking locations at random? |
| Bootstrap stability | PASS | 0.500 | ≥ 0.500 | Do the model's feature effects keep their sign across resamples? |
| Calibration | PASS | 0.059 | < 0.100 | When the model says 30%, is it right about 30% of the time? |
| Feature–label leakage | PASS | 0.147 | < 0.950 | Is any feature a disguised copy of the label? |

| Headline number | Value |
|---|---|
| PR-AUC, random cross-validation | 0.153 |
| PR-AUC, spatial block cross-validation (65 blocks) | 0.144 |
| Gap (the leakage the protocol looks for) | 0.009 |

## 3. Reviewer's reading

*The part a customer actually reads. Written by a person, for this model, in plain language.*

**The grade says the evaluation is honest. It does not say the model is good.** Those are
different questions, and this report answers the first one.

- **The number is real.** Random and spatial cross-validation agree to within 0.009. Whatever
  this model scores, it is not scoring it by memorising neighbouring points. That is the
  failure the audit exists to catch, and it is absent here.
- **The number is small.** Spatial PR-AUC of 0.144 against a class prior of 0.124 means the
  model ranks deposits about 16% better than chance. Two distance features are not enough to
  find Cr/PGM deposits on the Great Dyke. The audit confirms that honestly rather than
  flattering it.
- **One feature is less stable than the other.** Distance to intrusive keeps its sign in 100%
  of 200 bootstrap resamples. Distance to fault keeps it in 81%. The stability test passes
  exactly at its threshold (0.500), which is the weakest possible pass. Don't lean on the
  fault feature's direction.
- **Calibration is acceptable.** An expected calibration error of 0.059 means the
  probabilities can be read roughly at face value, though with 17 positives that estimate is
  itself noisy.

**If this were your model:** it is safe to describe the 0.144 figure to a board or an investor,
because it will hold up. It is not safe to describe the model as a targeting tool.

## 4. What this audit does not certify

- **Not a discovery guarantee.** PR-AUC measures how well known deposits are ranked, not what
  drilling will find.
- **Not transferable.** The result holds for this dataset and geology. A different orogen needs
  its own audit.
- **Not a check on your labels.** If the deposit list or the background sampling is biased,
  the audit measures the model against that bias faithfully.
- **Not a substitute for a Competent/Qualified Person.** The report is evidence a CP can use.
  It is not a resource statement and signs nothing.
- **Small-sample caveat.** 17 positives is enough to run every test and too few for tight
  confidence intervals. The report says so rather than hiding it.

## 5. Verify it yourself

Anyone can re-derive the certificate from the same inputs, on any machine:

```bash
pip install -e ".[api,audit]"
geomine audit benchmark/dataset.parquet benchmark/model.joblib --block-size-km 25.0
```

The certificate hashes the protocol version, the model's class and hyperparameters, the
dataset, and the quantised scores. If any of them change, the hash changes. That is what
makes the report checkable by someone who does not trust us.

## 6. What an engagement delivers

1. This report, for your dataset and model.
2. The machine-readable result (`audit.json`) with every test's full detail.
3. The certificate, and the exact command and inputs needed to re-derive it.
4. The thresholds used. The protocol defaults are public; any per-engagement changes are
   listed in the report.
