# HUMAN_QUEUE — founder-only actions (max five, most important first)

_Updated 29 Sep 2026. Outreach is paused until the MVP is finished — see `ops/DECISIONS.md`._

1. **Unlock GitHub billing (10 min).** CI is pushed but GitHub refused to start it: *"The job was
   not started because your account is locked due to a billing issue."* Fix it under
   github.com → Settings → Billing and plans. Actions are free for public repos, so this is an
   account lock, not a quota problem. Then re-run the failed CI run from the Actions tab.
   _If the cause is that a Zimbabwe-issued card was declined, note it for H5 below._
   _No default. Until this is fixed, nothing enforces the reproducibility promise._
2. **H5 bank call, by Fri 2 Oct.** Can a Zimbabwe entity receive USD/EUR from foreign clients
   for services? Account type, exchange-control/surrender rules, per-invoice paperwork, fees,
   timelines. Record the answer in `ops/DECISIONS.md`.
   _No default. A "no" changes what the invoice path needs._
3. **Host the API on Render (15 min, one sitting).**
   1. Sign up at render.com with your GitHub account.
   2. Create an API key for yourself (keep it somewhere safe; never commit it):
      `python3 -c "import secrets; print('founder:sk_live_' + secrets.token_urlsafe(24))"`
   3. In Render: New → Blueprint → pick `muudzo/mining`. It reads `render.yaml` and asks for
      `GEOMINE_API_KEYS`. Paste the line from step 2. Add more `id:secret` pairs, separated by
      commas, for anyone you give access.
   4. Paste the resulting `https://….onrender.com` URL into `ops/DECISIONS.md` so the landing
      page can link to it.

   **Plan choice.** Measured locally with Render-equivalent limits on the benchmark-sized audit:
   - **Free** (0.1 CPU): the audit takes about 16s. The service sleeps when idle, so the first
     request after a quiet spell also waits for a cold start. Costs nothing.
   - **Starter** (0.5 CPU): the audit takes about 1.1s and the service never sleeps. About
     $7/month [UNVERIFIED — check render.com/pricing], and it needs a card that works.

   _Default: Free, as `render.yaml` is written. Upgrade before sending the URL to a stranger._
4. **D1 — Launch date.** 30 Sep will pass without a launch. Record a new date in
   `LAUNCH_PLAN.md`, or record "launch = MVP done + outreach restarted".
   _Default: the latter._
5. **This repo is public.** `BRAINSTORM.md`, `AGENT_TEAM.md` and `ops/` are uncommitted on
   purpose, because pushing them would publish your internal strategy. Decide: (a) make the
   repo private until launch, (b) keep strategy docs local or in a separate private repo, or
   (c) publish them as they are.
   _Default: (b). They stay local._
