# Claims Audit

**Date:** 10 September 2026
**Scope:** every factual claim in the public-facing documents, checked against the code.
**Why this document exists:** the repository is public. A company whose product is independent
verification should be able to survive verification of itself. This is that check, run before
someone else runs it.

**Method:** each claim was traced to the code or artifact that would have to support it.
Verdicts are FALSE (contradicted by the code), UNSUPPORTED (no artifact exists either way),
UNVERIFIED (an external fact not checked here), or OK.

**Summary:** 6 FALSE, 4 UNSUPPORTED, 5 UNVERIFIED, 3 OK, as found on 10 September.

**Update, 11 September:** F2, F3 and F4 are fixed and independently verified -- the
reproduction command now works, a real certificate is published, and the certificate
binds the model and is stable across environments. U1/U2 (the unsupported "5/5, Grade A"
figures for the ViT) have been removed rather than substantiated, since no artifact
justifying them was found. U3/U4 (seeding and confidence intervals for the 0.453 figure)
remain open. See LAUNCH_PLAN.md's "Status as of 11 September" section for the full list
of what changed and what is still outstanding.

**Correction to that update, same day.** The paragraph above originally also claimed F1,
F5 and F6 were corrected "in BENCHMARK.md, README.md and the API's own docstrings." That
was true of BENCHMARK.md and the docstrings and false of everything else, and this
document did not notice. In fact:

- README.md's performance table still listed the model as "Prithvi-EO-2.0 ViT, fine-tuned"
  (F1), in the same file that tells a reader to verify our claims.
- ONE_PAGER.md still carried F1 in its technology table, F5 and F6 verbatim in its product
  descriptions, and additionally described the 0.453 figure as "audited, signed" -- directly
  contradicting its own headline section four paragraphs above, which correctly says that
  number "has not yet been run through the audit protocol."
- GEOMINE_AI.md listed Prithvi-EO-2.0 as a line item in the live stack table and in its
  "built with" footer.

All of those are now fixed. The lesson is recorded rather than quietly patched: **a claims
audit that marks an item corrected without re-grepping the tree is doing the thing it
exists to prevent.** Verify the fix the same way the original claim was checked -- against
the files, not against memory of having edited one of them.

---

## FALSE -- contradicted by the code

### F1. "Prithvi-EO-2.0 ViT (NASA/IBM)" is not the model

**Where:** ONE_PAGER.md technology table. GEOMINE_AI.md stack table. INVESTOR_DECK.md slide 7 in
its entirety.

**The claim:** that the Phase 2 result comes from NASA and IBM's Prithvi-EO-2.0, a transformer
"pre-trained on 4.2 million global satellite samples" which has therefore "already learned to
factor out illumination, vegetation seasonality, and atmospheric effects."

**What the code does:** `scripts/run_prithvi_loto.py` calls
`timm.create_model('vit_small_patch16_224', pretrained=True)`. That is ViT-Small, 22 million
parameters, pre-trained on ImageNet. The file's own docstring states it is "a simpler but
immediately runnable alternative to full Prithvi," and line 351 lists "actual Prithvi weights
(pre-trained on satellite data, not ImageNet)" as a future improvement.

**Why it matters most of the three.** Slide 7 is the reasoning for why Phase 2 should work at
all. That reasoning depends specifically on Earth-observation pre-training. An ImageNet model
has not seen a satellite image in pre-training, so the stated mechanism does not apply. This
claim is in a document used to raise money.

**Proposed fix:** state the actual model, and keep the hypothesis honest. "Phase 2 uses an
ImageNet-pre-trained ViT-Small with a six-band input adapter. Prithvi-EO-2.0 is the intended
backbone and is not yet integrated. The cross-tile result therefore comes from spatial context
alone, without Earth-observation pre-training, which we consider a lower bound rather than a
ceiling." That version is both true and a stronger story.

### F2. The reproduction command does not work

**Where:** ONE_PAGER.md. BENCHMARK.md.

**The claim:** run `geomine audit data/benchmark/dataset.parquet data/benchmark/model.joblib`
and the hash will match.

**Reality:** neither file exists, and `data/benchmark/` does not exist. A reader following the
instructions gets a file-not-found error. `*.joblib` is also gitignored, so the model could not
have been committed.

**Proposed fix:** publish the artifacts, or remove the instruction until they exist. Do not
leave a broken verification path in the document whose purpose is verification.

### F3. No certificate is published to compare against

**Where:** BENCHMARK.md instructs the reader to "compare the `certificate` field in your output
to the certificate published here."

**Reality:** no certificate hash appears anywhere in the file.

**Proposed fix:** publish the hash, or remove the instruction.

### F4. "Same data + same model = same hash" is false as implemented

**Where:** ONE_PAGER.md. BENCHMARK.md. The docstring on the certificate function itself.

**Reality, two separate defects:**

The certificate function signature is `_certificate(config, X, y, coords, scores)`. **The model
is not an argument.** Nothing about the model's class, parameters or weights enters the hash.
Two different models producing similar summary numbers collide. Swapping the model behind a
certificate is undetectable, which is the specific fraud the product exists to prevent.

The hash also covers full-precision floats produced by model fitting. A different maths library,
thread count or version shifts those floats in their last bits and changes the hash completely.
It additionally hashes raw memory layout, so the same data in a different column order hashes
differently. A customer verifying on a Mac against a number produced on Linux would very likely
see a mismatch, and the mismatch would look like dishonesty rather than floating point.

**Proposed fix:** hash the model identity and parameters, quantise the scores before hashing,
canonicalise array layout, and embed a protocol version. Until then the honest phrasing is
"reproducible within a pinned environment," not "same data plus same model."

### F5. `/v1/score` does not do what the one-pager says

**Where:** ONE_PAGER.md: "`POST /v1/score` takes a concession boundary, returns ranked
prospectivity zones with confidence scores."

**Reality:** the endpoint raises 501 unconditionally. It is a documented stub.

**Proposed fix:** describe targeting as a scoped engagement, which is what it is, and what the
501 body already says. The architecture review recommends keeping it a stub, and I agree.

### F6. `/v1/audit` does not audit the customer's model

**Where:** ONE_PAGER.md: "`POST /v1/audit` takes any binary classifier + labelled dataset and
runs the GeoMine validation protocol."

**Reality:** the endpoint ignores any notion of a customer model and always fits its own
`LogisticRegression` against the submitted data. The handler's own docstring admits it: "The
customer ships their own model? Not yet." Only the command line path accepts a model file.

**Proposed fix:** describe the hosted endpoint as a data leakage check and the command line as
the model audit. Keep them distinct in the copy, because they are distinct products.

---

## UNSUPPORTED -- no artifact exists either way

### U1. "Tests passed 5/5. Grade A."

**Where:** BENCHMARK.md. ONE_PAGER.md.

**Why it cannot be right as stated:** the Phase 2 model is a PyTorch module. The audit protocol
requires an object that scikit-learn can clone, refit and call `predict_proba` on, and the
bootstrap test requires coefficients or feature importances. The vision transformer has none of
these, so the audit cannot accept it, and the bootstrap test would return "unsupported," making
five out of five unreachable. Git history confirms the audit module was committed after Phase 2
closed. The audit also refits the model roughly 211 times per run, which is not feasible for a
transformer.

**This needs your input, not my edit.** Either these numbers came from a run not in the
repository, in which case publish it, or they were carried across from the Phase 1 logistic
regression work, in which case they must come out.

### U2. "Bootstrap stable feature fraction 0.83" and "Expected calibration error < 0.10"

**Where:** BENCHMARK.md. Same reasoning as U1, same question.

### U3. The headline 0.453 is not reproducible, including by you

**Where:** everywhere.

**Reality:** `scripts/run_prithvi_loto.py` sets no seed for torch, for numpy, or for the
dataloader shuffle, and uses dropout and a shuffled loader. Re-running it on the same machine
and the same data would not reliably return the same number. The chip inputs and the results
file were never committed.

**Proposed fix:** seed it, re-run it several times, and publish a range. A range is more
credible than a point estimate anyway, given the sample size.

### U4. Precision of "0.453" on 17 deposits

**Where:** everywhere, including "compliance-grade" framing aimed at lenders.

**Reality:** with this few positives spread across four folds, the confidence interval is wide
enough that the result is not cleanly separable from the Phase 1 number the team itself called a
failure. No interval is computed anywhere in the repository.

**Proposed fix:** publish an interval. State the number as evidence that cross-tile signal
exists, not as a performance guarantee.

---

## UNVERIFIED -- external facts not checked here

Market research is running and will settle these. They are not blocking, but they should not be
repeated to a lender until checked.

- **U5.** "$13 billion" annual exploration spend and "over 90% of exploration programmes fail."
- **U6.** Great Dyke as "world's second largest PGM reserve," and "300+ active concessions."
- **U7.** Platinum "$1,500-2,000+/oz in 2026" and ferrochrome "~$1,200/ton." Price claims date
  quickly and these were written in April.
- **U8.** "Total value of free data used: $50,000-200,000 per study region" and the
  "$70,000-270,000/year" commercial software equivalence. These read as generous.
- **U9.** "The drill hole classification algorithm has no precedent." A novelty claim needs a
  literature check before it is made in public.

---

## OK -- checked and fine

- **The line count is understated.** Documents claim 8,300 or more lines. Actual Python is 9,508
  across the package and scripts. Conservative claims are the right kind of wrong.
- **The Phase 1 failure narrative is accurate.** The collapse from 0.841 random cross-validation
  to 0.228 leave-one-tile-out, the class prior of 0.226, the coefficient sign flip between tiles,
  and the eight failed configurations are all consistent with the code and the committed results.
  This is the most credible material in the entire document set and it is the part that is true.
- **The data handling posture is genuinely good.** Customer data is processed in memory and never
  written to disk. Logs carry aggregate statistics only, never raw features or coordinates. There
  are no hardcoded secrets, configuration parsing is safe, and credentials come from the
  environment. This is better than most funded startups and it is worth stating publicly, before
  a job queue or an upload endpoint makes it untrue.

---

## Recommendation

The Phase 1 failure story is the asset. It is true, it is documented, and it is rare. Everything
in the FALSE list is a Phase 2 claim that reached further than the evidence, and every one of
them is fixable by describing what was actually built.

Fix F1 first. It is the one in the investor deck.

Nothing here requires abandoning the strategy. The audit protocol is still the right wedge and
the honest-failure narrative is still the right story. The corrections make both more defensible,
not less, because a company that publishes this document is demonstrating the exact discipline it
is trying to sell.
