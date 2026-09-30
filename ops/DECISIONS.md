# DECISIONS

Every decision, dated, with its reason. Newest at the top.

---

## 29 Sep 2026 — Pause outreach; finish the MVP first

**Decision (founder):** All prospect outreach is paused until the MVP below is finished. Cold
outreach restarts when it is done. No fixed restart date.

**MVP = "find, try, pay"** (the Sprint 2 gate in `LAUNCH_PLAN.md` §8). The scope is closed;
anything not on this list waits until after outreach restarts:

1. CI: full test suite, 96% coverage gate on the paid path (`geomine/audit`, `geomine/api`),
   and the benchmark reproduction from a clean checkout matching the certificate in
   `benchmark/manifest.json`. Build fails on mismatch.
2. The existing audit API hosted at one public URL, using the auth, rate limits and quotas
   already built.
3. A static landing page: what it is, the one command, a sample audit report, a way to reach
   the founder. No pricing page.
4. A sample audit report built from the benchmark, clearly labelled as a sample.
5. Invoice and audit engagement letter / SOW templates (liability clause flagged for legal
   review).

**Still happening this week:** the H5 bank call (can a Zimbabwe entity get paid
internationally?). It is not prospect outreach, and "pay" is part of the MVP.

**Reason given:** finish the product before asking strangers to look at it.

**Risk recorded:** this is the sequencing `BRAINSTORM.md` §7 argues against: the code queue
regenerates itself and the conversation queue does not start itself. The mitigation is that the
scope above is closed. Additions to it need a new entry in this file.

**Effect on `AGENT_TEAM.md`:** Pipeline is paused. Platform, Collateral (items 1, 4, 5 only),
Commercial and Research continue. §4 rule 9 ("conversations drive engineering") and the §8
gate are suspended until outreach restarts.
