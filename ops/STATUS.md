# STATUS

## STATUS — 29 Sep 2026

**Outreach: paused until the MVP is done** (`ops/DECISIONS.md`). Conversations: 0 / 20.

**MVP "find, try, pay": all five items are built. Three are blocked on founder actions.**

| # | Item | Built | Live | Blocked on |
|---|---|---|---|---|
| 1 | CI: tests, 96% coverage gate, certificate check | ✅ `6df049e` | ✗ | GitHub account billing lock (queue #1) |
| 2 | Hosted audit API | ✅ `d0d1a3c` | ✗ | Render setup + API key (queue #3) |
| 3 | Landing page | ✅ `e6b9390` | ✗ | Same Render blueprint (queue #3) |
| 4 | Sample audit report | ✅ `ee2afb0` | ✅ on GitHub | — |
| 5 | Engagement letter + invoice templates | ✅ `44a63de` | n/a | H5 answer, then lawyer/accountant review |

**Verified locally**
- CI steps in fresh venvs on Python 3.11.8 and 3.13.4: 98 passed, 96.27% coverage,
  certificate `c8bd3fd2…2100b` reproduced.
- Container at 0.5 CPU / 512 MB: health OK, `/v1/benchmark` serves the published certificate,
  no key → 401, benchmark-sized audit 1.05s. At 0.1 CPU (Render free): 16s.
- Landing page at 320/375/1440 px, light and dark, no horizontal overflow.

**Found, not fixed (outside the closed scope — note for later)**
- `ONE_PAGER.md` (public) still says "100x cheaper than drilling" and "Replaces $1M+ regional
  studies". The landing page doesn't repeat either claim. Both belong in the claims register.
- `POST /v1/audit` on the benchmark data returns certificate `e4b58b05…`, not the published
  `c8bd3fd2…`. The API always audits its own logistic-regression baseline, not the benchmark
  model, so the hashes differ by design. A stranger could still read that as "the hash doesn't
  match", so it needs one sentence in the API docs.
- The FastAPI description shown on `/docs` still says "Built on $0 infrastructure. Validated by
  failure."
- GitHub notice: `ubuntu-latest` moves to Ubuntu 26 from 19 Oct 2026. The certificate job will
  then also test the new OS. If it fails, that is the promise being checked, not CI noise.

**Blocked:** GitHub billing · Render account · H5 bank call. All three are founder actions,
listed in `ops/HUMAN_QUEUE.md`.
