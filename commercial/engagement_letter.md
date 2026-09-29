# Audit Engagement Letter — TEMPLATE

> **Template, not legal advice.** Text in `[BRACKETS]` must be filled in per engagement.
> Items marked **⚖ LEGAL REVIEW** must be checked by a lawyer before the first signature.
> Nothing here has been reviewed yet.

---

**Date:** [DATE]
**Engagement reference:** [GM-YYYY-NNN]

**Between**
GeoMine ("GeoMine"), [LEGAL ENTITY NAME, REGISTRATION NUMBER, ADDRESS] ⚖ LEGAL REVIEW:
the contracting entity depends on the H5 outcome in `ops/DECISIONS.md`.

**And**
[CLIENT LEGAL NAME, REGISTRATION NUMBER, ADDRESS] ("the Client"),
represented by [NAME, TITLE].

## 1. Scope

GeoMine will run the GeoMine audit protocol, version [v1], on the model and dataset described
below and report the results.

| | |
|---|---|
| Model | [MODEL NAME / DESCRIPTION], supplied as [FILE FORMAT, e.g. a scikit-learn-compatible `.joblib`] |
| Dataset | [DESCRIPTION], [N] rows, [N] labelled positives, coordinates in [CRS, projected metres] |
| Spatial block size | [25] km, unless agreed otherwise here: [ ] |
| Threshold changes from protocol defaults | [None / list each one] |

The protocol's five tests are: spatial leakage, beats class prior, bootstrap stability,
calibration, and feature–label leakage. Their definitions and default thresholds are
published in `geomine/audit/core.py` in the public GeoMine repository.

## 2. Deliverables

1. An audit report in the form of the published sample (`collateral/sample_audit_report.md`),
   including a plain-language reviewer's reading.
2. The machine-readable result (`audit.json`).
3. The certificate hash, and the exact command and inputs needed to re-derive it.

**Delivery:** within [N] business days of GeoMine receiving the complete model and dataset.

## 3. What the audit does not certify

The Client acknowledges that the audit:

- does not predict or guarantee exploration or drilling outcomes;
- applies only to the supplied dataset and geology, and does not transfer to others;
- measures the model against the supplied labels, and does not check those labels for bias
  or error;
- is not a Mineral Resource or Ore Reserve estimate, and is not a statement by a Competent or
  Qualified Person under JORC, NI 43-101, SAMREC, S-K 1300 or any similar code.

## 4. Client inputs and data handling

- The Client confirms it has the right to supply the model and dataset for this purpose.
- Loading a `.joblib`/pickle model file can execute code. GeoMine will load Client model files
  only in an isolated environment used for this engagement. [CONFIRM the actual setup before
  signing.]
- GeoMine will use Client materials only to perform this engagement, will not share them, and
  will delete them within [30] days of delivery unless the Client asks otherwise in writing.
  ⚖ LEGAL REVIEW: data-protection obligations in the Client's jurisdiction.

## 5. Confidentiality and publication

- The report belongs to the Client, who may share it with anyone, including investors and
  Competent Persons.
- GeoMine will not publish the report, name the Client, or refer to the engagement without the
  Client's written consent.
- A certificate hash on its own reveals nothing about the model or data.

## 6. Intellectual property

The Client keeps all rights in its model and data. GeoMine keeps all rights in the audit
protocol and its software, which remain open source under the repository's licence.

## 7. Fees and payment

| | |
|---|---|
| Fee | [CURRENCY] [AMOUNT] |
| Invoiced | [on signature / on delivery / 50% each] |
| Payment terms | [30] days from invoice date |
| Payment method | [PENDING H5, bank call due Fri 2 Oct 2026. See `ops/DECISIONS.md`] |

Fees exclude bank charges on the Client's side and any taxes the Client must withhold.
⚖ LEGAL REVIEW: withholding tax and VAT treatment of a cross-border service.

## 8. Limitation of liability

⚖ LEGAL REVIEW — placeholder only, not to be signed as written:
[GeoMine's total liability under this engagement is limited to the fee paid. GeoMine is not
liable for decisions the Client or third parties make on the basis of the report.]

## 9. Governing law

⚖ LEGAL REVIEW: [JURISDICTION]. Depends on the contracting entity (section header) and the
Client's location.

---

**For GeoMine:** ______________________ Name: [ ] Date: [ ]

**For the Client:** ______________________ Name: [ ] Date: [ ]
