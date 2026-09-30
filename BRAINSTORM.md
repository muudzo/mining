# Brainstorm -- Where GeoMine Actually Stands

**Written:** 29 September 2026
**Purpose:** altitude, not tasks. LAUNCH_PLAN.md is the task list and it is still broadly right.
This document exists to answer a different question: *what is the next month actually for?*

Read this one in a chair, not at a keyboard.

---

## 0. The one-paragraph version

The engineering half of the launch is essentially done and it is good. The commercial half has
not started. The launch date in LAUNCH_PLAN.md is tomorrow, three of its six launch criteria
are untouched, and the plan's own kill-criteria gate -- the mechanism designed to cheaply tell
us whether this entire wedge is wrong -- passed silently on 22 September because it had no
input. **The company knows almost exactly as much about its market today as it did on 10
September.** That, not the code, is the thing to fix.

---

## 1. The timeline, stated plainly

| Date | What the plan said would happen | What happened |
|---|---|---|
| 10 Sep | Plan written. Sprint 1 begins. Discovery outreach begins **Day 1, in parallel** | Plan written. Code work began |
| 11 Sep | -- | P0-1 reproducibility + P0-2 test suite committed |
| 14 Sep | -- | P0-3 auth, rate limiting, DoS bounds, claims corrections committed |
| 16 Sep | Sprint 1 gate: a stranger can reproduce the hash | Met (on 11 Sep, early) |
| 22 Sep | **Day 12: kill-criteria review.** 8 discovery calls held; decide whether the wedge survives | Nothing. No calls existed to review |
| 23 Sep | Sprint 2 gate: an external person can find, try and pay for the product | Not met. Nothing is hosted |
| 14--29 Sep | Sprint 2 and 3: deploy, landing page, outbound, first real audit | **15 days, no commits, no recorded activity** |
| 30 Sep | Launch | Tomorrow |

Two honest readings of the 15-day gap, and it matters which one is true:

1. **Life happened.** Solo founder, other obligations, energy ran out. Normal and forgivable.
2. **The work stopped being fun.** Everything left on the list is either unfamiliar (deploy,
   CI) or uncomfortable (cold outreach), and neither gives the clean pass/fail feedback that
   code does.

Only you know which. The plan's prescription is the same either way, but the *fix* is
different: reading (1) needs a smaller plan; reading (2) needs a different first action.

---

## 2. Launch criteria scorecard

From LAUNCH_PLAN.md section 0, scored honestly against the repo today:

| # | Criterion | Status |
|---|---|---|
| 1 | The reproducibility promise is true | **Met.** `geomine audit benchmark/...` returns `c8bd3fd2...` from a clean clone |
| 2 | Audit product live and paid-ready | **Partial.** Auth, rate limits, quotas, DoS bounds all done. Not hosted anywhere. No invoice path |
| 3 | Testable by a stranger | **Not met.** No landing page, no hosted demo, nothing a stranger can reach |
| 4 | Correctness defensible | **Partial.** 98 tests, 96% coverage on the paid path. No CI to gate it |
| 5 | 20+ conversations, 8+ discovery calls | **Not met.** Zero. No outreach artifacts of any kind exist |
| 6 | One real audit delivered | **Not met.** Depends on 5 |

One met, two partial, three untouched. **Every untouched item is a human-contact item.**
Every met or partial item is a code item. The pattern is not subtle.

---

## 3. The diagnosis

The plan predicted this failure precisely, in its own words, on day zero:

> "Discovery outreach begins on Day 1 in parallel -- the list gets built while the code gets
> fixed, **because conversations have latency and code does not.**"

It also flagged the mechanism in the risk register: *"Founder bandwidth: one person, seven
tracks."* The forecast was correct. The mitigation ("agent parallelism, ruthless section 9")
worked for the code tracks and did nothing for the human ones, because agents can write a rate
limiter and cannot have a conversation with a mining executive on your behalf.

Why this happens, without moralising about it: **code returns a verdict in seconds and
outreach returns one in weeks, often as silence.** Under time pressure, any rational agent
optimises toward the loop with the tighter feedback and the lower rejection rate. That is what
happened. It is the single most common way technically strong solo founders spend a year
building something nobody buys, and the only known antidote is to make the slow loop start
*first*, because it is the one with latency.

I should name my own part in this. The last two working sessions -- auth, rate limiting,
streaming body-size guards, concurrency caps, a claims audit of the claims audit -- were
correct, genuinely closed a real launch blocker, and were also exactly the kind of work that
feels like decisive progress while the actual risk sits untouched. The code got better. The
business learned nothing.

---

## 4. What the delay actually bought

Not nothing. This is worth being fair about, because it changes the opening move.

On 10 September, starting a conversation meant leading with a product whose central public
promise was broken: a reproduction command pointing at files that did not exist, a certificate
that did not bind the model, and three false claims in the one-pager.

Today the position is: *"Run this one command. You get this exact hash. Here is the protocol,
here is what it refuses to certify, and here is a published audit of our own overclaims."*

**That is a materially stronger thing to walk into a conversation with**, and it is rare enough
to be the opening line rather than the footnote. The 19 days were not wasted -- they were spent
on the wrong axis at the wrong time, which is different from being wasted.

---

## 5. The five questions worth actually thinking about

### Q1. What does "launch" mean now?

The date is tomorrow. Three options, and the plan already rules out the dishonest one:

- **Move the date.** The plan says "the date moves before the standard does." Clean, honest,
  and costs nothing externally because nobody outside knows the date exists.
- **Redefine launch as a technical release.** Publish the repo and the protocol publicly with
  no commercial claims attached. This is achievable in days, produces a real artifact, and is
  a legitimate thing to point conversations at.
- **Launch commercially anyway.** Not available. There is nothing hosted to sell and nobody to
  sell it to.

Worth noticing: the launch date was always self-imposed. No investor, customer or partner is
waiting on 30 September. What is the date actually *for*? If the honest answer is "to create
urgency," it has already done its job and can be re-set without loss.

### Q2. Is the audit actually the wedge?

H1 through H5 in LAUNCH_PLAN.md section 5 are all still completely untested. Not
partially -- **zero data points on any of them.** The whole strategy rests on H1 (someone with
budget feels pain from unverifiable AI claims) and nobody has ever checked.

The kill-criteria gate was designed to make this cheap to discover by 22 September. It did not
fire because it had no input. So the strategy has not survived a test; it has merely avoided
one. Those feel similar and are not.

### Q3. What is the smallest thing that produces outside signal?

Ranked by information-per-day-of-effort, roughly:

1. **Ten conversations.** No deploy required, no landing page required, no CI required. The
   product as it exists today is demonstrable over a screen share or a single command in a
   terminal. This tests H1, H3 and the mandate question simultaneously.
2. **Publish the negative result.** The plan already argues this is "potentially the
   highest-credibility, lowest-cost customer acquisition channel available to a company with
   no network, because it converts the failure into authority." Slow to land, so it should
   start early -- same latency logic as outreach.
3. **Deploy to a URL.** Genuinely useful, one to three days of work, and it makes conversation
   #11 easier. But it is not the bottleneck, and it will feel like the bottleneck because it
   is the one on this list that is fun.

### Q4. The mandate problem

The plan names this as Critical and it remains unanswered: **no regulation requires validation
of an AI-derived exploration target.** SR 11-7 makes model risk management sell. JORC and NI
43-101 make Competent Persons sell. Nothing makes this sell.

Without a mandate the audit is bought out of fear, vanity or diligence. Those are real
motives -- they are just weaker, slower and less predictable than compliance, and they change
who the buyer is. This question cannot be answered from inside the repository. It is a
conversation question and a desk-research question, and it may be the single highest-stakes
unknown in the company.

An angle worth testing that the plan does not cover: the demand may sit with **whoever carries
liability** rather than whoever buys the model. A Competent Person signing off on a resource
statement informed by an AI target has personal professional exposure. That is closer to a
real mandate than anything on the vendor side.

### Q5. H5 -- can a Zimbabwe entity actually get paid?

Still unchecked, still structural. This one is different from the others because it is not a
market question, it is a plumbing question with a definite answer that someone at a bank can
give you this week. If the answer is no, entity structure becomes a P0 and the scope narrows
before anyone says yes -- not after, when a signed customer is waiting to pay and cannot.

**This is the cheapest open question in the entire plan and it has been open for 19 days.**

---

## 6. Assumptions nobody has tested

| Assumption | Basis today | Cheapest real test |
|---|---|---|
| Buyers feel pain from unverifiable AI claims | Inference from the field | 10 conversations |
| That pain is worth $5,000 | Intuition. Plan says so outright | Ask what they spent last time they doubted a model |
| AI vendors will pay to be audited | Assumption; they may treat it as a threat | 3 conversations with vendors |
| Buyers care about the hash, not just the grade | Assumption | Show both, see which they ask about |
| Zimbabwe entity can invoice internationally | Unchecked | One call to a bank |
| $25K targeting report is priced right | Intuition | Ask what a conventional target costs them |
| Mining-AI competitors don't publish spatial CV | Believed, drives the whole thesis | An afternoon reading competitor materials |
| The negative result is publishable | Unassessed | One email to an academic in the field |

Eight load-bearing assumptions. **Seven are testable in under a week and none have been
tested.** The eighth (pricing) needs the conversations anyway.

---

## 7. What I would argue, if you want a position to push against

Deliberately stated as a position, not a recommendation, so it is easier to disagree with:

1. **Stop writing code for two weeks.** Not because the remaining code is worthless -- CI and
   a deploy genuinely matter -- but because the code queue will always regenerate itself and
   the conversation queue will not start itself. The product is already past the bar needed to
   have the conversation.
2. **Move the launch date to 31 October and say so in LAUNCH_PLAN.md.** Not as a slip, as a
   decision, with the reason written down: the engineering gate was met, the commercial gate
   was never attempted, and a 20-day plan that allocated one founder across seven tracks was
   optimistic about the two that involve other humans.
3. **Run the Day 12 gate late rather than never.** Eight conversations, then honestly ask
   whether validation doubt came up unprompted. Answering that question in October is still
   cheap. Answering it in March is not.
4. **Do H5 this week.** One call. It is the only open question with a definite answer and it
   can invalidate the business model independent of everything else.
5. **Treat the deploy as the reward, not the prerequisite.** Do it after the first five
   conversations, when you know what those people actually asked to see.

The case against all of this: conversations without a hosted product convert worse, the
negative-result preprint is slow, and a technical founder's comparative advantage genuinely is
the technical work. That case is not stupid. It is just the same gradient that produced the
last 19 days, wearing a strategy costume.

---

## 8. What not to spend the next month on

Extending LAUNCH_PLAN.md section 9, with one addition:

- **More of what the last two sessions did.** The API is bounded, authenticated, rate-limited,
  tested at 96% and honest about its own limits. Further hardening is now premature
  optimisation against a load that does not exist, for customers who do not exist yet.
- Improving the 0.453. It does not gate the audit product at all.
- Finishing `/v1/score`. Still a quarter of work.
- Any dashboard, map viewer, or QGIS plugin.
- Rewriting the April documents. GEOMINE_AI.md and INVESTOR_DECK.md are now correctly marked
  as superseded; that is sufficient until someone actually asks for a deck.

---

## 9. Prompts for the actual brainstorm

Not rhetorical. Worth writing an answer to each.

1. If you could only do **one** of these in October -- ten conversations, or a deployed product
   with a landing page -- which produces more information, and which are you more likely to
   actually do? If those answers differ, that gap is the real problem to solve.
2. What would have to be true for the audit wedge to be *wrong*? What would you expect to hear
   in the first three calls if it is?
3. Who is the single most likely first customer, by name? If no name comes to mind, is that a
   market problem or a network problem? They have very different fixes.
4. The plan says the honest-failure story is the durable asset. Is it a **product** wedge or a
   **credibility** asset that sells something else? Those lead to different companies.
5. What does the next 30 days look like if the audit turns out to be a vitamin? Is there a
   version of this where the negative result and the protocol are published as open work, and
   the revenue comes from targeting engagements while the protocol builds the reputation?
6. Honestly: what is the thing you have been avoiding? It is probably the highest-value item
   on the list, and it is probably a conversation.

---

*The engineering is genuinely ahead of most of the field. The company still has no evidence
that anyone will pay for it. Both things stay true until someone outside this repository is
asked a question.*
