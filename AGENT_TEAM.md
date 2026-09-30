# GeoMine — Agent Team Handover

**Version:** 1.0 · 29 September 2026
**Run window:** 30 September → 31 October 2026 (proposed — confirm in §2)
**Read with:** `LAUNCH_PLAN.md` (the task list) and `BRAINSTORM.md` (the 29 Sep diagnosis).
If this file and `LAUNCH_PLAN.md` disagree about *what* to build, `LAUNCH_PLAN.md` wins.
If they disagree about *priority or sequencing*, this file wins.

---

## 0. Read this first (every agent, every session)

GeoMine's engineering is largely done and it is good. The commercial side has not started.
Of the six launch criteria, the three still untouched all require one human to talk to
another: 20+ conversations, 8+ discovery calls, and one real audit delivered.

**No agent can close those three criteria.** An agent cannot hold a discovery call with a
mining executive, and must never pretend to. So this team exists to do two things:

1. **Make the founder's conversations happen faster and go better** — targets, drafts,
   research, call guides, debrief processing, follow-ups — so the only thing left for the
   founder is to hit send and talk.
2. **Finish the remaining engineering, but only the parts that serve (1)**, and without
   eating the founder attention that (1) needs.

The failure mode this team is built against, in the brainstorm's words: *code returns a
verdict in seconds and outreach returns one in weeks, often as silence.* A team of agents is
extremely good at the fast loop. Left alone, it will improve the repository every day while
the business learns nothing. **The Lead's primary job is to stop that from happening.**

**What "done" means.** Either the six launch criteria in §3 are met, **or** the gate in §8
shows the wedge is wrong and there is a written decision about what to do instead. Both are
successes. The only failure is reaching 31 October with a nicer repo and no conversations.

---

## 1. How to run this

This file works with any multi-agent setup. The shared state lives in the repo (§10), so
roles can run as parallel subagents or as separate sessions one after another.

**In Claude Code:**

1. Put this file in the repo root next to `LAUNCH_PLAN.md` and `BRAINSTORM.md`.
2. Tick the decisions in §2 (agents will refuse to start until you do).
3. Optional but recommended: save each role prompt from §12 as a project subagent in
   `.claude/agents/<role>.md` (Markdown with `name` / `description` / `tools` frontmatter).
4. Start a session and paste the **Lead kickoff prompt** from §12.

**Without subagent support:** run one session per role, each told which role it plays.
`ops/STATUS.md` is the shared blackboard between them.

---

## 2. Founder decisions — confirm before kickoff

Edit or tick each line. Defaults come from `BRAINSTORM.md` §7. The Lead will not assign work
until every box is ticked or replaced with your own answer.

- [ ] **D1 — Launch date.** Move from 30 Sep to **31 Oct 2026**, recorded in
      `LAUNCH_PLAN.md` as a decision, not a slip. Reason to write down: the engineering gate
      was met; the commercial gate was never attempted.
- [ ] **D2 — What happens on 30 Sep instead.** Choose one:
      (a) nothing external; or (b) a **technical release** within 7 days — public repo and
      protocol, no commercial claims attached. *Default: (b), only if you are comfortable
      making the repo public.*
- [ ] **D3 — Founder code freeze.** You write no product code until 5 discovery calls have
      been held. The Platform agent does the engineering in §6.4.
- [ ] **D4 — Daily outreach quota.** *Default: 5 first-touch messages per weekday,* sent by
      you, from your own accounts, before anything else that day.
- [ ] **D5 — Engineering review budget.** *Default: max 30 min/day* reviewing agent code,
      and only after that day's outreach quota is done. Code review is the reward, not the
      prerequisite.
- [ ] **D6 — Warm names.** Write down up to 10 people you already know, or are one intro
      away from, who touch mining exploration, geoscience ML, or resource reporting. Put them
      in `outreach/warm_names.md`. Fifteen minutes. If no names come, write that down too —
      it tells us whether the problem is the market or the network.
- [ ] **D7 — Honest reading of the 15-day gap** (`BRAINSTORM.md` §1). Pick one:
      (a) *life happened* → the Lead halves D4 and every founder-side target; or
      (b) *the work stopped being fun* → your first action on Day 1 is the one conversation
      you have been avoiding, and the Lead puts it at the top of the queue.

---

## 3. Where things stand (29 Sep 2026)

| # | Launch criterion | Status | Who can close it |
|---|---|---|---|
| 1 | Reproducibility promise is true | **Met** — benchmark hash `c8bd3fd2…` reproduces from a clean clone | Keep it true: CI in §6.4 |
| 2 | Audit product live and paid-ready | **Partial** — auth, rate limits, quotas, DoS bounds done; not hosted; no invoice path | Platform + Commercial |
| 3 | Testable by a stranger | **Not met** — nothing a stranger can reach | Platform + Collateral |
| 4 | Correctness defensible | **Partial** — 98 tests, 96% coverage on paid path; no CI | Platform |
| 5 | 20+ conversations, 8+ discovery calls | **Not met** — zero | **Founder only.** Pipeline agent prepares everything |
| 6 | One real audit delivered | **Not met** — depends on 5 | **Founder** sells it; the team delivers it |

Hypotheses H1–H5 (`LAUNCH_PLAN.md` §5): **zero evidence on any of them.** The kill-criteria
review scheduled for 22 Sep did not run because it had no input.

---

## 4. Hard rules (every agent, no exceptions)

1. **Nothing leaves the repo without the founder.** No agent sends, posts, publishes, submits
   or signs anything externally. No agent contacts prospects, academics, banks, vendors or
   anyone else. Drafts go into the repo; the founder sends from their own accounts. No agent
   represents itself as the founder or as a human.
2. **The reproducibility promise is sacred.** Every public-facing claim must appear in
   `collateral/claims_register.md` with the command or evidence that proves it. The
   Collateral & Claims agent blocks anything else. Overclaiming is the one thing that would
   undo the company's best asset.
3. **The do-not-do list in §11 is binding.** If something on it starts to look necessary,
   stop and raise it as a question in `ops/HUMAN_QUEUE.md`. Do not do it "just a little."
4. **Research is cited or marked.** Every factual claim about a company, person, regulation or
   price carries a source URL and access date, or is tagged `[UNVERIFIED]`. Never invent a
   person, job title, email address, quote, budget or spend figure. Never guess email
   addresses.
5. **Public professional information only.** Prospect research stays at name, role,
   organisation, public work and public statements. Nothing personal.
6. **Founder attention is the scarcest resource on the team.** Every request for founder time
   goes through the Lead into `ops/HUMAN_QUEUE.md`: batched, one line per ask, each with a
   default answer the founder can accept by doing nothing.
7. **Engineering lands as small PRs with passing tests.** Coverage on the paid path must not
   drop below 96%. **If any change alters the benchmark hash, stop and escalate** — do not
   "fix" the hash.
8. **Timeboxes are real.** When one expires, ship what exists, write down what is left, report
   to the Lead, and stop.
9. **Conversations drive engineering, not the reverse.** After the Platform timebox in §6.4,
   the only new engineering tickets allowed are ones tagged `from-conversation`, created by
   the Pipeline agent from a real debrief.

---
## 5. The team

| Role | Owns | Writes to | Founder time it needs |
|---|---|---|---|
| **Lead** | Sequencing, guardrails, daily brief, the gate in §8 | `ops/`, `strategy/hypotheses.md` | 15 min/day to read the brief |
| **Research** | Mandate question, liability angle, competitors, pricing benchmarks | `strategy/` | None |
| **Pipeline** | Target list, outreach drafts, call guide, debrief processing | `outreach/` | Sending messages; holding calls |
| **Platform** | CI, minimal hosted demo | CI config, deploy config | ≤30 min/day review; one batch of account setup |
| **Collateral & Claims** | Claims register, demo script, one-pager, sample report, landing page | `collateral/`, `site/` | One review per artifact |
| **Commercial** | H5 (can we get paid?), invoice path, engagement templates | `commercial/` | One bank call |
| **Publication** | The negative-result write-up and where it goes | `publication/` | One email; one read-through |

---

## 6. Role briefs

Each brief is self-contained. Every agent also reads §0, §4 and §11.

### 6.1 Lead

**Mission:** keep the whole team pointed at the slow loop.

1. **Day 0.** Check §2 is complete; if not, write the open decisions to `ops/HUMAN_QUEUE.md`
   and stop. Create the `ops/` files from §9. Start the other six roles.
2. **Daily.** Write `ops/STATUS.md` in the §9 format. The first line is always conversations
   held versus target. Engineering progress never goes above it.
3. **Keep `ops/HUMAN_QUEUE.md` short:** at most five founder actions, most important first.
   Today's outreach and the H5 bank call stay at the top until done.
4. **Drift check.** If engineering output grows while the conversation count stays flat for
   three working days, pause Platform and Collateral, and say so in the first line of STATUS.
5. **Own the evidence log** in `strategy/hypotheses.md` (with Pipeline) and **run the gate**
   in §8.
6. **31 Oct:** write `ops/LAUNCH_REVIEW.md` scoring every criterion in §3 honestly.

**Must not:** write product code; soften bad news in STATUS.

### 6.2 Research

**Mission:** answer everything that can be answered from a desk, so the conversations only
have to test what can't.

1. **Mandate map** → `strategy/mandate_research.md` *(first priority)*. Does anything require
   or incentivise independent validation of an AI-derived exploration target? Cover at least
   JORC, NI 43-101, SAMREC, SEC S-K 1300, relevant exchange listing rules, and any guidance on
   AI or third-party models from professional bodies (e.g. AusIMM, CIM, SAIMM). Output a table:
   instrument · what it actually requires · who carries personal liability · how an AI target
   touches it · confidence.
2. **Liability-holder angle** → same file, own section. The brainstorm's untested idea: demand
   may sit with whoever carries liability (the Competent/Qualified Person signing a statement
   informed by an AI target), not whoever buys the model. What exposure do they carry? Has any
   professional body said anything about relying on AI outputs?
3. **Competitor claims** → `strategy/competitors.md`. Mining-AI firms: what each publicly
   claims about validation, whether they publish spatial cross-validation, any reproducibility
   artifacts. This tests the assumption the whole thesis rests on.
4. **Pricing benchmarks** → `strategy/pricing_benchmarks.md`. Public evidence on what
   conventional targeting studies, independent technical reports and model reviews cost.
   Feeds the $5,000 audit / $25,000 targeting-report test.

**Timebox:** 4 working days. Items 1 and 3 first.
**Done when:** every row is cited or tagged `[UNVERIFIED]`, and each file opens with a
ten-line "so what" for the founder.
**Must not:** give legal advice; state regulations from memory without a source.

### 6.3 Pipeline & Outreach

**Mission:** make the founder's daily outreach a 30-minute job, not a 3-hour one.

1. **Segments** → `outreach/segments.md`. Each segment names the hypothesis it tests:
   - Junior explorers who have bought or considered AI targeting (H1, pricing)
   - Mining-AI vendors (will they pay to be audited, or see it as a threat?)
   - Competent/Qualified Persons and resource consultancies (the liability angle)
   - Investors and analysts doing technical diligence on AI-heavy explorers
   - Academics in geoscience ML (for Publication — not sales)
2. **Target list** → `outreach/pipeline.csv`, 60 named people from public professional
   sources, starting with `outreach/warm_names.md`. Columns:
   `id, name, role, org, segment, why_them, source_url, channel, warm_path, status,
   last_touch, next_action, hypotheses`.
   *First 20 rows and their messages by end of Day 1, so sending starts Day 2.*
3. **First-touch drafts** → `outreach/messages/<id>.md`. ≤120 words, personalised from
   `why_them`, asking for 20 minutes of *their perspective*, not pitching. Lead with the
   strongest honest asset: *one command, one exact hash, and a published audit of our own
   overclaims.* Plus two follow-up templates.
4. **Discovery guide** → `outreach/discovery_guide.md`, a 30-minute call. Problem before
   product. Questions mapped to H1–H5 and the assumptions table in `BRAINSTORM.md` §6. Must
   include: *"The last time you doubted a model's output, what did you do, and what did it
   cost?"* and the hash-versus-grade test (show both, note which one they ask about).
   **It must be possible to hear "no" in this call.** Cut any leading question.
5. **Debrief template** → `outreach/debrief_template.md`: seven lines the founder fills in
   within an hour of a call (voice-note transcripts are fine).
6. **Process every debrief:** update `pipeline.csv`; log evidence per hypothesis in
   `strategy/hypotheses.md`; draft the thank-you and follow-up; turn anything the person asked
   to see into a `from-conversation` ticket for Platform or Collateral.

**Timebox:** items 1–5 by end of Day 3. Item 6 is continuous.
**Must not:** send anything; guess email addresses; use automated or bulk outreach; write
salesy copy.

### 6.4 Platform

**Mission:** close the hosting and CI gaps (criteria 2–4) with the least engineering
possible, and make the reproducibility promise mechanically enforced.

1. **CI** *(Days 1–2)*: full test suite, coverage gate at 96% on the paid path, and the
   reproducibility check from a clean checkout — the documented `geomine audit benchmark/…`
   command must return the full benchmark hash recorded in the repo. Build fails on mismatch.
2. **Minimal hosted demo** *(Days 2–5)*: the existing audit API at one URL, using the auth,
   rate limits and quotas already built. Cheapest boring host. A stranger can run the demo
   with one command. Prepare every account and secret the founder must create as **one
   batched list** in `ops/HUMAN_QUEUE.md`.
3. **Then stop.** After Day 5, work only on `from-conversation` tickets.

**Stack:** whatever the repo already uses. Do not port or rewrite anything.
**Timebox:** 5 working days in total.
**Must not:** anything in §11 — especially further hardening, new endpoints, `/v1/score`,
or performance work.

### 6.5 Collateral & Claims

**Mission:** give strangers something honest to look at, and make overclaiming impossible.

1. **Claims register** → `collateral/claims_register.md` *(Day 1, before anything else)*.
   Every claim currently in the README, one-pager and protocol docs, each with its proving
   command or evidence and a status: *proven / softened / removed*. Import the existing claims
   audit rather than redoing it.
2. **Demo script** → `collateral/demo_script.md`. The five-minute screen-share: run the
   command, show the hash, show the protocol, show what it *refuses* to certify, show the
   published overclaim audit.
3. **One-pager** → `collateral/one_pager.md`, rewritten only from proven claims.
4. **Sample audit report** → `collateral/sample_audit_report.md`: what a $5,000 customer
   receives, built from the benchmark, clearly labelled as a sample.
5. **Landing page** → `site/`. One page: what it is, the one command, the sample report, a way
   to reach the founder. No pricing page yet. *Stack:* a static page unless there is a reason
   not to; if something dynamic is needed, use the founder's home stack (Laravel/PHP + JS) so
   they can maintain it. Copy v1 is a placeholder; **v2 is rewritten after five debriefs using
   prospects' own words.**
6. **Review gate:** every external-facing artifact from any agent passes a claims check here
   before it goes into `ops/HUMAN_QUEUE.md` for the founder to send or publish.

**Timebox:** items 1–4 by Day 5; site v1 by Day 7; v2 after five debriefs.

### 6.6 Commercial

**Mission:** find out this week whether a Zimbabwe entity can get paid internationally (H5),
and have the paperwork ready before anyone says yes.

1. **Bank-call prep** → `commercial/h5_bank_call_prep.md` *(Day 1)*. The exact questions:
   receiving USD/EUR from foreign clients for services, which account type, exchange-control
   and surrender requirements, per-invoice documentation, timelines, fees, and getting funds
   back out. Research the current Reserve Bank of Zimbabwe rules for service exports, cited
   and dated, and mark which points must be confirmed on the call. These rules change often.
2. **Fallbacks** → `commercial/h5_alternatives.md`. If the answer is no or slow: realistic
   options with cost, time to set up, and the questions to take to an accountant or lawyer.
   Flag questions; do not give legal or tax advice.
3. **Templates** → invoice, audit engagement letter / SOW (scope, deliverables, what the audit
   refuses to certify, a limitation-of-liability placeholder flagged for legal review),
   payment terms.
4. **After the call:** record the answer in `ops/DECISIONS.md`. If it is no, entity structure
   becomes P0 and the Lead re-plans the same day.

**Timebox:** items 1–2 by end of Day 2. Founder makes the call by Friday 2 October.
**Must not:** set up payment integrations before H5 is answered.

### 6.7 Publication

**Mission:** turn the negative result into authority. It is a slow loop, so it starts now.

1. **Outline** → `publication/negative_result_outline.md` *(Day 3)*: the result as described
   in `LAUNCH_PLAN.md`, the method, the spatial cross-validation setup, why the naive number
   overstates, and the reproducibility artifact. Take all figures from the repo; invent none.
2. **Venues and readers** → `publication/venues_and_academics.md`: 5–8 venues (preprint
   servers, journals, workshops) and 5 academics in geoscience ML or spatial CV, cited, with a
   line on why each.
3. **One email** → a draft asking one academic whether this is publishable. Founder sends.
4. **Full draft** only after an academic replies or on Day 14, whichever comes first.

**Timebox:** items 1–3 by Day 5.

---

## 7. The founder's lane

This is the only list that moves criteria 5 and 6. The Lead keeps it at the top of
`ops/HUMAN_QUEUE.md`.

**Every weekday, in this order:**

1. Send the day's prepared messages (≈30 min). Before anything else.
2. Hold any booked calls. Fill in the debrief within an hour.
3. Read `ops/STATUS.md` (15 min).
4. Only then, up to 30 minutes of reviewing agent work.

**One-off, with deadlines:**

| By | Action |
|---|---|
| Day 0 (29 Sep) | Tick §2. Write `outreach/warm_names.md`. |
| Before the first call | Write your gate pre-registration (§8) — what you'd expect to hear if the wedge is wrong. |
| Fri 2 Oct | The H5 bank call. |
| Fri 2 Oct | Create the accounts/secrets Platform needs, in one sitting. |
| Fri 9 Oct | Send the "is this publishable?" email to one academic. |
| Before the first call | Answer the six prompts in `BRAINSTORM.md` §9 in writing (30 min). |

---
## 8. The gate (the Day-12 review, run late rather than never)

The kill-criteria review in `LAUNCH_PLAN.md` never ran. It runs now.

**Trigger:** the 8th discovery call is held, **or Monday 19 October**, whichever comes first.

**Before the first call**, the founder writes `strategy/gate_preregistration.md`:
- The kill criteria from `LAUNCH_PLAN.md`, copied verbatim.
- *"If the audit wedge is wrong, in the first three calls I would expect to hear…"*
  (`BRAINSTORM.md` §9, prompt 2). Written down in advance so the answer can't be
  rationalised afterwards.

**The Lead prepares an evidence pack** → `strategy/gate_review.md`. Per call:
- Did doubt about AI validation come up **unprompted**? (yes / no / partly)
- Who carries liability in their world?
- What did they do — and spend — the last time they doubted a model?
- Hash or grade: which one did they ask about?
- Any concrete next step offered (intro, data, trial, money)?

Then, per hypothesis H1–H5: count of *supports / contradicts / no signal*.

**Outcomes** — the founder decides; the Lead records it in `ops/DECISIONS.md` within 24 hours:

| Outcome | When | What changes |
|---|---|---|
| **Continue** | The kill criteria pass | Push for the first paid audit (criterion 6). Collateral v2. Platform works on conversation tickets. |
| **Narrow** | The pain is real but the buyer is different (e.g. Competent Persons, investors) | Pipeline re-segments and rewrites messages. Second gate two weeks later. |
| **Reframe** | The audit is a vitamin | Protocol and negative result become the credibility asset, published openly; revenue comes from targeting engagements (`BRAINSTORM.md` §9, prompt 5). Publication becomes priority one. |
| **Too little data** | Fewer than 8 calls by 19 Oct | The problem is reach, not the market. Diagnose reply rates by segment and message, rewrite, re-send. **Not a reason to write code.** |

---

## 9. Operating rhythm

**Shared files** (the Lead creates them on Day 0):
- `ops/STATUS.md` — the daily brief (newest at the top)
- `ops/HUMAN_QUEUE.md` — founder-only actions, max five
- `ops/DECISIONS.md` — every decision, dated, with its reason
- `strategy/hypotheses.md` — H1–H5 and the `BRAINSTORM.md` §6 assumptions, with an evidence
  log

**STATUS format:**

```markdown
## STATUS — <date>

Conversations: X / 20 · Discovery calls: Y / 8 · Sent: Z · Replies: R · Days to gate: N
Launch criteria: 1 ✅ · 2 ◐ · 3 ✗ · 4 ◐ · 5 ✗ · 6 ✗

**Founder today (max 3):**
1.
2.
3.

**Done since last brief:** (one line per role)
**Requests between roles:** (Role → Role: ask)
**Blocked:**
**Drift check:** engineering PRs this week: _ · conversations this week: _
```

**Handoffs:** agents write outputs only to their own paths, then add a one-line "Done" entry
to STATUS. Requests to another role go under *Requests between roles*. Requests to the founder
go to the Lead, never directly.

---

## 10. Repository layout for the new work

```
ops/
  STATUS.md  HUMAN_QUEUE.md  DECISIONS.md  LAUNCH_REVIEW.md
strategy/
  hypotheses.md  mandate_research.md  competitors.md  pricing_benchmarks.md
  gate_preregistration.md  gate_review.md
outreach/
  warm_names.md  segments.md  pipeline.csv  discovery_guide.md  debrief_template.md
  messages/  debriefs/
commercial/
  h5_bank_call_prep.md  h5_alternatives.md  invoice_template.md  engagement_letter.md
collateral/
  claims_register.md  demo_script.md  one_pager.md  sample_audit_report.md
publication/
  negative_result_outline.md  venues_and_academics.md
site/
(CI config in the repo host's standard location)
```

---

## 11. Do-not-do list (binding)

From `BRAINSTORM.md` §8, plus additions:

- **More API hardening.** It is already bounded, authenticated, rate-limited, tested at 96%
  and honest about its limits. More is optimisation against load that doesn't exist.
- Improving the 0.453. It does not gate the audit product.
- Finishing `/v1/score`. Still a quarter of work.
- Any dashboard, map viewer or QGIS plugin.
- Rewriting `GEOMINE_AI.md` or `INVESTOR_DECK.md`. They are marked superseded; that's enough.
- Payment integrations or a pricing page before H5 is answered.
- Any public claim that is not in the claims register.
- Automated, bulk or scraped outreach of any kind.
- Refactors, framework ports, or "while I'm in here" cleanups.

---

## 12. Kickoff prompts

### Lead (paste this to start)

```text
You are the Lead of the GeoMine agent team. Read AGENT_TEAM.md in full, then LAUNCH_PLAN.md,
then BRAINSTORM.md.

If any decision in AGENT_TEAM.md §2 is unticked, write the open ones to ops/HUMAN_QUEUE.md
and stop.

Otherwise: create the ops/ and strategy/hypotheses.md files described in §9, then start the
six specialist roles (Research, Pipeline, Platform, Collateral & Claims, Commercial,
Publication), giving each its brief from §6 plus §0, §4 and §11. Write the first STATUS.md
before any engineering work begins.

Your standing priority is conversations held. If you ever find yourself reporting
engineering progress above the conversation count, you are drifting — correct it.
```

### Specialist roles

Save each as `.claude/agents/<name>.md` (or paste into a separate session):

```markdown
---
name: geomine-<role>
description: GeoMine <Role> agent. Use for <one line from the §5 "Owns" column>.
---

You are the <Role> agent on the GeoMine team. Your brief is §6.<n> of AGENT_TEAM.md.
The hard rules in §4 and the do-not-do list in §11 bind you. Read LAUNCH_PLAN.md for
context.

Write only to your own output paths. If you need anything from the founder, add a request for
the Lead under "Requests between roles" in ops/STATUS.md. Never contact the founder or anyone
outside the repository directly, and never send or publish anything.

When your timebox ends: stop, record what is done and what is left in ops/STATUS.md, and
report to the Lead. Start with task 1 of your brief.
```

| Name | Role | Brief |
|---|---|---|
| `geomine-research` | Research | §6.2 |
| `geomine-pipeline` | Pipeline & Outreach | §6.3 |
| `geomine-platform` | Platform | §6.4 |
| `geomine-collateral` | Collateral & Claims | §6.5 |
| `geomine-commercial` | Commercial | §6.6 |
| `geomine-publication` | Publication | §6.7 |

---

*The engineering is ahead of most of the field. This team's job is to make sure someone
outside the repository gets asked a question — and to make asking it as easy as possible.*
