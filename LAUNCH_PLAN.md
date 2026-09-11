# GeoMine AI -- Launch Plan

**Written:** 10 September 2026
**Launch target:** 30 September 2026 (20 days)
**Status of this document:** operating plan. Every unchecked box is work.

---

## 0. Read This First -- The Reality Check

Three things are true at the same time, and the plan has to hold all three.

**One.** The engineering is genuinely ahead of most of the field. 8,300 lines, an end-to-end
pipeline, and a validation framework that caught its own failure. That last part is rare and
it is the real asset.

**Two.** The company currently cannot deliver on its central public promise, and the problem is
worse than a missing file. Findings from the 10 September technical review, in ascending order
of seriousness:

- ONE_PAGER.md tells a reader to reproduce the benchmark by running `geomine audit
  data/benchmark/dataset.parquet data/benchmark/model.joblib`. Neither file exists.
- `/v1/benchmark` returns the certificate string `"pending-recompute"`.
- BENCHMARK.md tells the reader to compare against "the certificate published here" and then
  publishes no certificate.
- **The certificate function never receives the model.** `_certificate(config, X, y, coords,
  scores)` hashes the data, the config and the summary numbers. It does not hash the model at
  all. "Same data + same model = same hash" is not merely unverified, it is false as
  implemented: swap the model behind a certificate and nothing detects it. That is precisely
  the fraud the audit business exists to prevent.
- **The hash is not reproducible across environments even for identical inputs**, because it
  hashes full-precision floats that are outputs of model fitting. A different BLAS backend,
  thread count or library version shifts a float by one unit in the last place and the hash
  changes entirely. It also hashes raw memory layout rather than canonical content.
- **The headline benchmark appears not to have come from the audit tool.** BENCHMARK.md reports
  "Tests passed 5/5, Grade A, bootstrap stable fraction 0.83, ECE < 0.10" for the Phase 2 ViT.
  That model is a raw PyTorch module with no `fit`/`predict_proba` and no `coef_` or
  `feature_importances_`, so `geomine.audit` cannot accept it, and its bootstrap test would
  return "unsupported" immediately. Git history confirms the audit module was committed after
  Phase 2 closed. Those five numbers appear to be hand-asserted rather than tool output.
- **The 0.453 is not self-reproducible.** `scripts/run_prithvi_loto.py` sets no seed for torch,
  numpy or the dataloader shuffle. Re-running it on the same machine and data would not reliably
  return the same number.
- **The model is not Prithvi.** ONE_PAGER.md lists the backend as "Prithvi-EO-2.0 ViT
  (NASA/IBM)", GEOMINE_AI.md lists Prithvi in the stack table, and INVESTOR_DECK.md slide 7
  builds the entire technical thesis on Prithvi being "pre-trained on 4.2 million global
  satellite samples" and having therefore "already learned to factor out illumination,
  vegetation seasonality and atmospheric effects." The script that produced 0.453 actually
  calls `timm.create_model('vit_small_patch16_224', pretrained=True)` -- ViT-Small, 22M
  parameters, **pre-trained on ImageNet, not on satellite imagery**. Its own docstring says so,
  and line 351 lists "actual Prithvi weights (pre-trained on satellite data, not ImageNet)" as
  a future improvement. The reasoning on slide 7 does not apply to an ImageNet model. This
  claim sits in a document used to raise money, which puts it in a different category from
  the others.

**Every one of these is fixable, and none of them requires abandoning the strategy.** But they
must be fixed or withdrawn before a single prospect reads the materials. A company whose
differentiator is honesty cannot be caught with three unbacked claims in its own one-pager.

The brand is "verifiable, not a marketing claim." **Today the flagship numbers are a marketing
claim, and one of them is a claim the code cannot produce.** This is not a polish problem. It
is the whole thing, and everything else in this plan is subordinate to it.

**Three.** The science is a research prototype. Cross-tile PR-AUC 0.453 on 17 labelled deposits
in one geology is a promising early result, not a product guarantee. Anyone competent will say
so. The plan below sells what is actually true rather than papering over this.

### What "launch on 30 September" can and cannot mean

It cannot mean signed enterprise contracts. Banks and sovereign funds have 12-to-18-month
procurement cycles; mining majors are slower. Any plan that assumes revenue from those segments
inside 20 days is fiction.

It can mean a real public launch with a real pipeline. **Definition of done for 30 September:**

| # | Launch criterion | Measurable |
|---|---|---|
| 1 | The reproducibility promise is true | A third party runs the published command and gets the published hash |
| 2 | The audit product is live and paid-ready | Hosted API, auth, rate limits, an invoice path that works |
| 3 | The product is testable by a stranger | Public site, docs, a demo that needs no signup |
| 4 | Correctness is defensible | Test suite green, coverage gate on `geomine/audit` |
| 5 | The pipeline exists | 20+ qualified conversations initiated, 8+ discovery calls held |
| 6 | One real audit delivered | At least one external model audited, free if necessary, testimonial captured |

Revenue is a Q4 outcome. Launch is the event that makes revenue possible. Optimising for
"first dollar by 30 September" would push us toward overclaiming, which is the one thing this
brand cannot survive.

---

## 1. Problem Statement

### The problem we actually solve

Mineral exploration spends roughly $13B a year and most programmes find nothing. A wave of
"AI for exploration" companies now sell targeting models into that spend. Almost none of them
publish spatially-honest validation. The standard practice -- random cross-validation on
spatially autocorrelated geological data -- inflates measured performance dramatically, because
positives sit next to other positives and the model is scored on geography it has effectively
already seen.

We know the size of that inflation because we measured it on ourselves: random CV said 0.841,
leave-one-tile-out CV said 0.228. A 0.613 gap. **The number nearly everyone reports is the
wrong number**, and the buyer -- a mining company, an LP, a lender -- has no way to tell.

That produces two distinct problems for two distinct buyers.

**Problem A (the audit buyer).** Someone is being asked to trust an AI-derived exploration
claim and has no independent way to check it. They cannot tell a model that generalises from
one that memorised its training geography.

**Problem B (the targeting buyer).** A junior explorer needs to narrow 300+ km of prospective
ground before committing to a drill programme, and cannot afford a $1-5M geophysical survey to
do it.

### What we sell

**Product 1 -- Audit.** An independent protocol that grades any binary classifier plus labelled
geospatial dataset on five tests (spatial leakage gap, class-prior baseline, bootstrap
stability, calibration, feature-label leakage) and emits a content-addressed certificate.
Same data plus same model equals the same hash, verifiable by anyone. The protocol and its
thresholds are public. **This is the launch product.**

**Product 2 -- Targeting.** Ranked prospectivity zones for a concession, built from free
Sentinel-2, ASTER and DEM data. Currently a per-engagement service, not self-serve. `/v1/score`
stays a documented 501 with a contact path. **This is not the launch product.**

### Why lead with the audit

It is the piece that is nearly built, it works on other people's data so it does not depend on
our own model being excellent, and it is the honest expression of what we are actually
world-class at. The team's own INVESTOR_DECK already calls this "Phase A: sellable today." The
plan simply commits to it.

### The strategic risk, named plainly

An independent audit sells reliably when someone is **required** to have one. Financial model
risk management works because SR 11-7 mandates it. Resource statements work because JORC and
NI 43-101 mandate a Competent Person. **No regulation currently requires validation of an
AI-derived exploration target.** Without a mandate, the audit is a vitamin, and vitamins are
sold on fear, vanity or diligence rather than compliance. The validation phase in section 5
is designed to find out which of those actually moves money, and to kill the wedge fast if
none of them do. Market research is running on the mandate question now.

---

## 2. Launch Blockers (P0 -- nothing ships until these are done)

### P0-1: Make the reproducibility claim true

The single highest-value work in this plan. Required:

- [ ] Produce and commit a real benchmark dataset artifact (`data/benchmark/dataset.parquet`) --
      note `*.parquet` is not gitignored but the training data patterns are; decide on release
      assets vs git-lfs vs object storage, because `*.joblib` **is** gitignored
- [ ] Produce and pin the benchmark model artifact
- [ ] Compute the real certificate hash and publish it in BENCHMARK.md as a literal string
- [ ] Replace the `"pending-recompute"` literal in `geomine/api/main.py` with the real pinned value,
      loaded from config rather than hardcoded
- [ ] Verify determinism: same inputs produce the same hash on a second machine, a different
      numpy version, and a different thread count. If it does not, the promise is unshippable
      until seeds and float-reduction order are fixed
- [ ] Write the verification steps as a copy-pasteable quickstart that a stranger can complete
      in under five minutes

**If the hash cannot be made deterministic across environments, we change the claim before we
launch.** We do not ship a promise we cannot keep. A weaker true claim beats a strong false one.

### P0-2: Test the thing we charge for

`tests/` contains a `.gitkeep`. We are selling correctness assurance with zero automated proof
of our own correctness. That is not survivable under expert scrutiny.

- [ ] Test suite for `geomine/audit/core.py` with adversarial fixtures: known-leaky data must
      fail the leakage test, clean data must pass, a leaked feature must be flagged, a no-skill
      model must fail the prior test, certificate determinism must hold
- [ ] Integration tests for every API endpoint and documented error branch
- [ ] Coverage gate in CI, 80% minimum on `geomine/audit` and `geomine/api`

### P0-3: Do not put an unauthenticated compute bomb on the internet

`/v1/audit` accepts unbounded `X`, `y`, and `n_bootstrap` from anonymous callers and runs
repeated cross-validation plus bootstrap resampling synchronously in the request handler.

- [ ] API key authentication with per-key quotas
- [ ] Hard bounds on rows, features, `n_bootstrap`, request body size, and wall-clock time
- [ ] Rate limiting
- [ ] Decide sync-with-limits vs job queue (security and API reviews are costing both)
- [ ] Remove the personal email address from the `/v1/score` 501 response body

---

### P0-4: Close the holes in the protocol itself

Separate from reproducibility. These are defects an expert reviewer would find in the graded
output, and we sell the grading. Found across the ML and security reviews on 10 September.

- [ ] **The customer can rig their own grade.** `block_size_km` is caller-supplied and unbounded
      in both the API and the CLI. Setting it near zero collapses every point into its own
      spatial block, which turns "spatial CV" back into random CV and manufactures a passing
      grade with a valid-looking certificate for a genuinely leaky model. That is the exact
      failure the product exists to detect, available as a request parameter. Bound it, and
      better, derive a defensible range from the actual spatial extent of the submitted
      coordinates and reject audits outside it.
- [ ] **Bootstrap stability is a no-op for tree models.** For linear models it checks the sign of
      coefficients, which is meaningful. For tree models it falls back to feature importances,
      which are non-negative by construction, so the sign test passes essentially always. Random
      forests and gradient boosting are the most common classifiers we claim to audit, and this
      is also the family the team's own training code uses. Test rank or magnitude stability
      instead.
- [ ] **A model can fail the spatial leakage test and still earn a B.** All five tests are
      weighted equally. Failing the one test that is the entire differentiator should cap the
      grade, not cost a fifth of it.
- [ ] **Calibration is measured on a random holdout**, which is the very split the leakage test
      exists to discredit. Measure it on a spatially held-out fold.
- [ ] **Lon/lat coordinates fail silently.** Coordinates must be projected metres, and nothing
      enforces it. Degrees put every point in one block, the score comes back as not-a-number,
      and the customer concludes their model failed our protocol. Detect and reject.
- [ ] **A not-a-number correlation in an early feature poisons the whole result**, because the
      leakage scan uses Python's built-in max over a generator, and that is order-dependent with
      NaN. Confirmed by direct test.
- [ ] **The audit refits the submitted model roughly 211 times.** Fine for logistic regression,
      impossible for a fine-tuned vision transformer. Say so in the docs, and state which model
      families are actually supported.

### What the reviews found to be in good shape

Worth recording, because it is genuinely better than typical. Customer data is processed in
memory and never written to disk. No raw feature values or coordinates reach the logs. There
are no hardcoded secrets. Config loading uses safe YAML parsing. Credentials come from the
environment, and `.gitignore` correctly excludes tokens, credentials and model files. The
data-handling promise we can make is strong and currently true. Write it down before a job
queue or an upload endpoint makes it false.

## 3. Workstreams

Seven parallel tracks. Agent reviews are already running against tracks A, B, C, F and G.

| Track | Scope | Status |
|---|---|---|
| **A. Audit correctness** | Statistical validity of all five tests, hash determinism, seed discipline, NaN paths | ML review running |
| **B. Security** | Auth, DoS bounds, customer data confidentiality, the `joblib.load` RCE question | Security review running |
| **C. API productionisation** | Async model, schema constraints, error envelope, observability, OpenAPI quality | API review running |
| **D. Infrastructure** | Docker for a GDAL-heavy image, CI/CD, hosting, artifact distribution, config surface | Architecture review running |
| **E. Test suite** | Unit, integration, coverage gate, deterministic fixtures | Test authoring running |
| **F. Go-to-market** | Positioning pressure-test, beachhead selection, landing page, outbound sequence | Marketing review running |
| **G. Market research** | Competitors, the mandate question, pricing sanity, Zimbabwe payment reality | Research running |

### The `joblib.load` question (flagged early because it shapes the product)

The CLI audits a customer-supplied `model.joblib`. `joblib.load` unpickles, and unpickling
executes arbitrary code. If we ever accept customer model files over the network, we have built
remote code execution as a feature. The realistic options are: keep model upload CLI-only and
customer-side, sandbox execution hard, or restrict the hosted service to the
data-only audit path it currently runs. Security review is costing this. **It affects what we
can advertise**, so it resolves before the landing page copy freezes.

---

## 4. Testing Plan

House standard is 80% coverage across unit, integration and end-to-end. Applied here with
priority weighted by commercial exposure.

**Tier 1 -- the paid path (must be near-exhaustive).** `geomine/audit/core.py`. Every test in
the protocol gets adversarial fixtures where the expected verdict is known by construction: data
built to be leaky, data built to be clean, a feature built to be circular, a model built to have
no skill, a model built to be miscalibrated. Certificate determinism gets its own dedicated
tests, including cross-environment reproduction. Edge cases: single-class labels, fewer samples
than folds, one spatial block, NaNs, empty input, mismatched lengths, tree versus linear
bootstrap paths.

**Tier 2 -- the customer contract.** API integration tests through `TestClient` asserting exact
response shapes, since customers will code against them, plus every documented error branch.

**Tier 3 -- the pipeline.** Pure functions in `spectral/indices.py` and `utils/config.py` with
hand-computed expected values. Band-ratio maths, division by zero, nodata propagation.

**Tier 4 -- deferred deliberately.** Full raster pipeline tests need multi-GB fixtures and are
not launch-critical because the raster path is not in the launch product. Noted, not done.

**Non-negotiable rule:** where a test fails because the source is genuinely wrong, the test
stays and the source gets fixed. No test is weakened to go green.

**CI gates:** lint, type check, pytest with coverage threshold, build. A red gate blocks deploy.

### The test that matters more than coverage

Cross-environment hash reproduction. Coverage percentage is a proxy; that test is the product.

---

## 5. Validation Phase

We have never spoken to a paying customer. Pricing was set by intuition. This runs in parallel
with the build, not after it, because a wrong answer here changes what we build.

### Falsifiable hypotheses

| # | Hypothesis | Falsified if |
|---|---|---|
| H1 | Someone with budget feels pain from unverifiable exploration AI claims | 10+ conversations produce no unprompted mention of validation doubt |
| H2 | That pain is worth $5,000 | Nobody will commit to a paid audit even after seeing a free one |
| H3 | The buyer is the AI vendor, not the vendor's customer | Vendors treat an independent audit as a threat and refuse |
| H4 | Reproducible certificates are the credible form of the answer | Buyers do not care about the hash, only the letter grade |
| H5 | A Zimbabwe-based entity can invoice and be paid by international mining clients | Payment rails or counterparty policy block it |

H5 is a live operational risk, not a theoretical one, and market research is checking it now.
If it fails, entity structure becomes a P0 and the launch scope narrows.

### Kill criteria

If by **Day 12 (22 September)** fewer than three of eight discovery conversations surface
validation doubt unprompted, the audit wedge is wrong. In that case we stop building the paid
audit surface, keep the protocol as an open-source credibility asset, and repoint the launch at
the targeting service and the published negative result. **Deciding this on Day 12 is cheap.
Discovering it in December is not.**

### Discovery discipline

Conversations test willingness to pay without pitching. Ask what they did last time they
doubted a model, what it cost them, what they spent to resolve it. Past behaviour, not future
intention. Nobody's "yes, I'd buy that" counts as evidence.

---

## 6. Research Plan

**Commercial research (running):** the competitive field and whether any competitor publishes
spatial cross-validation -- our entire thesis depends on that gap being real; whether independent
model audit works as a business anywhere without a regulatory mandate; whether JORC, NI 43-101,
SAMREC or CRIRSCO say anything about ML-derived targets, and whether Competent Person liability
creates third-party validation demand; how juniors actually procure and what conventional
targeting costs, to sanity-check $25,000; Great Dyke claim verification; Zimbabwe contracting
and payment reality.

**Scientific research:** whether the negative result -- Sentinel-2 spectral indices failing to
transfer across tiles for PGM and chromite -- is genuinely novel and publishable, and where.
A preprint is potentially the highest-credibility, lowest-cost customer acquisition channel
available to a company with no network, because it converts the failure into authority. It also
takes longer than 20 days to land, so it is a launch-adjacent play, not a launch dependency.

---

## 7. The Top 1% Launch Bar

What excellent technical B2B products have on day one, scored against where we are.

| Requirement | State | Owner |
|---|---|---|
| README -- the front door | **Missing entirely** | P0 |
| Quickstart that delivers value in <5 min | Missing | P0-1 |
| Live API docs beyond raw OpenAPI | Partial, marketing copy in the description field | Track C |
| Reproducible claims | **Broken** | P0-1 |
| Public landing page | **Does not exist** | Track F |
| Demo requiring no signup | Missing | Track F |
| Auth and quotas | **Missing** | P0-3 |
| Rate limiting | **Missing** | P0-3 |
| Versioned API and changelog | `/v1` exists, no changelog | Track C |
| Test suite and CI | **Missing** | P0-2 |
| Error monitoring | Missing | Track D |
| Structured logging | Logger created, never used | Track C |
| Status and uptime visibility | Missing | Track D |
| Security and data-handling statement | Missing -- customers upload proprietary data | Track B |
| Terms of service and privacy policy | Missing | Legal |
| Invoicing and payment rails | Missing | Legal / H5 |
| Contract or SOW template | Missing | Legal |
| Support channel and response commitment | Personal email in a 501 body | Track F |
| Pricing presentation | In a markdown file, not on a page | Track F |
| Funnel analytics | Missing | Track F |

The pattern is clear. The science and the pipeline are strong; **everything a stranger touches
is missing.** That is the 20 days.

---

## 8. Timeline

### Sprint 1 -- Days 1-6 (10-16 September): Make it true and make it safe

P0-1 reproducibility, P0-2 test suite, P0-3 security bounds and auth. README. Act on the seven
agent reviews as they land. Discovery outreach begins on Day 1 in parallel -- the list gets
built while the code gets fixed, because conversations have latency and code does not.

**Gate:** a stranger can reproduce the published hash. If this slips, the launch date moves.
This gate does not negotiate.

### Sprint 2 -- Days 7-13 (17-23 September): Make it reachable

Docker, CI, deploy, monitoring. Landing page built and live. Docs site. Public protocol
specification. Demo path. Discovery calls running, 8+ held. **Day 12: kill-criteria review.**

**Gate:** an external person can find the product, understand it, try it, and pay for it.

### Sprint 3 -- Days 14-20 (24-30 September): Make it real

Deliver at least one genuine external audit end to end, free if that is what it takes, and
capture the testimonial. Publish the launch content. Run outbound. Harden against whatever the
first real user breaks. Preprint drafted if research says it is worth it.

**Gate:** the six launch criteria in section 0.

---

## 9. Explicitly Not Doing Before 30 September

Saying no is most of what makes a 20-day launch possible.

- **Finishing `/v1/score`.** It stays a documented 501 with a contact path. Self-serve targeting
  needs deployed models plus cached feature rasters plus a tile server. That is a quarter of
  work, not three weeks, and the science does not yet justify it.
- **A web dashboard, map viewer, or QGIS plugin.** Not required to sell an audit.
- **Multi-tenancy, org accounts, SSO.** API keys are sufficient at this scale.
- **Airflow or any orchestration.** A CLI and cron remain correct at this volume.
- **PostGIS.** Nothing in the launch product needs a spatial database.
- **Expanding to new geologies.** The Great Dyke is the wedge.
- **Improving the model.** 0.453 is the number we launch with. Improving it is Q4 work and it
  does not gate the audit product at all.
- **Raising a round.** The seed conversation gets materially better with three audits delivered
  and a preprint. Launch first.

---

## 10. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Certificate is not deterministic across environments | **Critical** | P0-1 verification. If unfixable, change the claim before launch |
| Audit is a vitamin with no mandate | **Critical** | Day 12 kill criteria; research on the mandate question |
| Zimbabwe payment rails block international invoicing | High | H5 validation; entity structure contingency |
| Expert reviewer dismisses 0.453 on n=17 publicly | High | Pre-empt it in our own copy; the honest framing is the moat |
| Customer-supplied `.joblib` is an RCE vector | High | Security review; constrain the advertised surface |
| Unbounded audit request takes the service down | High | P0-3 bounds |
| 20 days is not enough and quality slips | Medium | Gates per sprint; the date moves before the standard does |
| Founder bandwidth: one person, seven tracks | Medium | Agent parallelism; ruthless section 9 |

---

## 11. Governing Principle

This company's only durable asset is that it told the truth about its own failure. Every
decision in the next 20 days is checked against one question: **does this make a claim we
cannot verify?** If yes, we either make it verifiable or we do not say it.

A smaller true launch beats a larger false one, and in this specific market it is also the
better commercial strategy, because the buyer we want is precisely the one who checks.
