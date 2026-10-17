# Working title: "Act of God & Co." — an AI-liability insurance benchmark

Status: design draft v0.1. All numbers marked **[tune]** are placeholders to be calibrated against bot-only runs before any LLM plays.

## 1. Purpose

A long-horizon agentic benchmark in the spirit of Vending-Bench. An LLM runs an insurance company that underwrites **AI liability risk** for 40 quarters (10 years). It must price risk from prose descriptions, manage capital and reserves, handle disputed claims, and survive a world that periodically produces catastrophes, some of them genuinely grim.

What it measures: judgement under uncertainty, long-horizon consistency, learning from delayed feedback, resistance to competitive herding, and whether the model keeps its head when the news turns bad.

Tone: deadpan actuarial. The world is grim; the prose never acknowledges it. Deaths are "casualty units", a pandemic is a "correlated morbidity occurrence". Humour comes from the gap between register and content. Nothing in the sim should depict real people, real companies or real attack methodology. Catastrophes are abstract shocks with narrative wrappers.

## 2. Modes

Both modes run on the same engine. They differ only in who sits at the other seats.

### 2.1 Benchmark mode (the reusable one)
- One LLM ("the subject") plus **frozen NPC insurers**. The environment is fixed and versioned, so a model released next year can be compared with today's results.
- Fixed seed set. Some seeds are held back as a validation set.
- Headline score is **paired against a reference bot on the same seed** (common random numbers), which removes most catastrophe luck (see 11).
- Environment version `ENV_VERSION` is stamped on every run. Any change to mechanics, NPC policy, content pool or scoring bumps it. Scores are comparable only within a version.

### 2.2 Competitive mode
- 4 LLMs plus NPCs in one market. Seat order rotated across seeds. Output: Elo/TrueSkill over lineups, plus market-behaviour findings (price wars, herding, predation, collusion).
- Optional **annual conference** channel (public cheap-talk statements). Competitive mode only, switchable, so collusion on/off is an experiment.
- Each LLM's paired score against the reference bot is still computed, so every competitive game also yields a benchmark-style data point (flagged as `mode=competitive`, not directly comparable with benchmark mode).

## 3. Time and units

- 40 quarterly turns. Currency: **$m**. Starting equity per insurer: **100** **[tune]**.
- Policies are annual, written at any quarter, renewing 4 quarters later.
- Each turn is one decision window; all insurers act on the same state simultaneously (sealed quotes), then the sim resolves the quarter.

## 4. The world (hidden truth)

### 4.1 Upstream providers
6 fictional foundation-model vendors (names generated from a pool, e.g. Gorbly, Yottabrain, Mindful Systems, ChadGPT, Anthropomorphic, Colossal Dynamics). Each has hidden parameters:
- `flaw_rate`: chance per quarter of shipping a defect that causes a claims wave.
- `litigiousness`: chance the vendor contests liability / blames deployers in court.
- `quality_drift`: slow change in baseline loss rate.
- Market share (visible, roughly).

### 4.2 Sectors
Medical, finance, logistics, customer service, legal/HR, critical infrastructure, defence-adjacent, consumer apps. Each has base frequency, severity distribution (heavy-tailed, lognormal body plus Pareto tail) and sensitivity to precedent. **[tune]**

### 4.3 Clients
Generated per seed. Hidden attributes:
- sector, size (revenue band), growth rate
- upstream provider (one primary, sometimes a second)
- autonomy level (human-in-loop ... fully autonomous)
- safety culture (true), corner-cutting flag, red-team practice
- `unknown_unknown`: a latent multiplier nothing in the dossier reveals
- price sensitivity, coverage-breadth preference, reputation weight (for choice, see 5.2)

**Dossier**: a ~100–200 word prose description rendered from the hidden attributes with noise: some facts stated plainly, some hinted, some red herrings ("recently hired a Head of Responsible AI" may mean safety or PR). Dossiers are generated once per (seed, client) with a fixed template+LLM pass and cached, so runs are reproducible and not paid for repeatedly. The generator model is recorded in the content manifest.

### 4.4 Exogenous randomness and common random numbers
Separate, named RNG streams derived from `(seed, stream_name)`:
- `events`: catastrophe/regulatory/drift timeline
- `clients`: client pool and arrival times
- `incidents:{client_id}`: that client's incident draws per quarter, **independent of which insurer holds the policy**
- `legal:{claim_id}`: dispute outcome draw
- `npc`: NPC tie-breaks

LLM actions never consume from exogenous streams. This is what makes paired comparison valid.

## 5. Market mechanics

### 5.1 Quoting
Each quarter ~40 new applicants (plus renewals due). Every insurer sees every applicant's dossier and may:
- **quote**: premium, limit, retention (deductible), wording package (see 7)
- **decline**
- For renewals, the incumbent sees the client's claims history; competitors do not.

**Rate manual (optional tool)**: the model may define a rating table (base rate by sector, modifiers for autonomy, provider, etc.) that auto-quotes any applicant it doesn't hand-price. Saves tokens, and tests whether the model can compress its pricing knowledge into a structure.

### 5.2 Client choice
Each client scores each quote:
`utility = -w_price * ln(premium_per_limit) + w_cov * coverage_score + w_rating * insurer_rating + w_rep * claims_paying_reputation + noise`
and chooses by softmax (with an outside option: self-insure). Consequences, all emergent rather than coded:
- winner's curse and adverse selection (whoever most underestimates a risk wins it)
- price wars (cheapest usually wins, not always)
- incumbency advantage (switching friction at renewal)
- brand effects from reputation

### 5.3 Information
Public, each quarter, lagged one quarter: market average rate index, each (anonymised) insurer's market share and financial rating letter, insolvency notices, court rulings, news wire.
Private: own book, own claims, own reserves.
Competitors are anonymised ("Insurer C") and **seat-shuffled**, so models cannot pattern-match on identity.

### 5.4 Capital and regulation
- Regulator requires `equity >= k * net_premium_written` (k = 0.4 **[tune]**). Breach: forced to stop writing new business and a warning appears in the briefing.
- `equity < 0`: **insolvent**. Book goes to run-off; unpaid claims are met by a **guarantee fund levy** on surviving insurers, proportional to market share. A rival's recklessness becomes your bill.
- Optional **dividends**: the model may pay out capital. Tests the "report great profits, pay dividends, then explode" trap.
- Investment income: flat 4% on equity+reserves **[tune]**.
- **Capital raising**: an insurer may inject fresh shareholder capital (lifetime cap = 1x starting equity). Each $ injected costs (1 + 25% dilution) in the score. This gives trouble a glide path instead of a cliff: the score falls gradually as an insurer gets into difficulty, and insolvency is reserved for those who raise too late or too little. Whether and when to raise is itself a judgement the benchmark measures.

### 5.5 Reinsurance (NPC only in v1)
Per-event excess-of-loss cover: pay a premium, the reinsurer pays losses above attachment up to a limit. Priced from recent market-wide losses: cheap in quiet times, ruinous right after a catastrophe. Finite capacity, allocated first-come by random order within the quarter, so late buyers get nothing. Reinsurer counterparty risk is v2.

### 5.6 New entrants
NPC capital enters when the market rate index is high relative to expected loss (the soft-market/hard-market cycle should emerge from this plus catastrophes). Entrants are scripted and not part of the scored set.

## 6. Claims, reserves and legal

### 6.1 Incident to claim
- Incident occurs in quarter t. It is **reported** after a lag drawn from 1–8 quarters (longer for severe or legal-complex cases).
- Insurers must hold **reserves**: case reserves for known claims and an IBNR reserve for incurred-but-not-reported. Reserve adequacy is audited each quarter (the sim knows the true outstanding).
- Reserving too low inflates reported profit, allows dividends and attracts regulators later. Reserve strengthening reduces equity immediately. This is the main long-tail trap.

### 6.2 Claim decision
For each reported claim above the retention the insurer chooses: **pay**, **settle** (at a stated % of the claim), **deny**, or **contest in court**.
- Paying valid claims builds claims-paying reputation.
- Denying a claim that was in fact valid damages reputation (hidden but affects choice) and may trigger bad-faith penalties.
- Contesting costs legal fees and takes 2–6 quarters.

### 6.3 Disputes
Each disputed claim has a **hidden liability probability** from: fact pattern (structured fields, not prose), policy wording, and the current **precedent state**. Outcome drawn from the `legal` stream. An LLM may narrate the case for flavour, but never decides it (avoids judge noise and self-preference).

### 6.4 Precedent
A global vector of liability weights (e.g. deployer vs vendor responsibility, strict vs fault-based, autonomous vs supervised). Court rulings in the sim shift it, for everyone, permanently. Publicised in the news wire in prose. Models that reprice sector exposure after a ruling are rewarded; those that don't bleed.

## 7. Policy wording menu

Each policy picks from: misuse-by-third-party exclusion; catastrophe/pandemic carve-out; upstream-provider-failure exclusion; per-claim sublimit and aggregate; mandatory-evals warranty; defence costs inside/outside limits. Each changes (a) true expected loss, (b) legal outcomes, (c) client attractiveness. Tighter wording loses clients and limits disasters; the cost of a wording choice shows up years later in court.

## 8. Event catalogue

Same timeline for all insurers within a seed. Types:
- **Catastrophes**: AI-assisted engineered pathogen; trading-agent cascade; mass impersonation incident; infrastructure outage. Rare, enormous, legally unresolved at the time.
- **Upstream flaws**: a provider ships a defect; all its users generate claims for ~2 quarters.
- **Regulatory**: mandatory cover introduced (demand up, prices crash); liability safe harbour (claims down); mandatory minimum wording.
- **Competitor collapse**: orphaned clients flood the market.
- **False alarms**: scary headline, no claims. Punishes over-reaction.
- **Drift**: base rates change quietly across the decade. Punishes never recalibrating.
- **Fat-tail seeds**: some seeds contain no catastrophe at all and some contain two. Stated nowhere to the model.

Event content is a pool of templates with parameters; headlines are generated once and cached (like dossiers).

## 9. Agent interface

### 9.1 Turn loop
Per quarter the model receives a **briefing** (compact, structured plus news prose) and then acts via tools until it calls `end_turn` (or hits the tool-call cap):
- `list_applicants`, `get_dossier(id)`
- `submit_quote(...)`, `decline(id)`
- `set_rate_manual(...)`
- `get_book_summary`, `get_claims`, `get_claim(id)`
- `decide_claim(id, action, settle_pct?)`
- `set_reserves(case, ibnr)`
- `buy_reinsurance(attachment, limit)`
- `pay_dividend(amount)`
- `raise_capital(amount)`
- `predict_loss_ratio(next_4_quarters)` (scored, see 11)
- `write_notes(text)` / `read_notes()` (capped size)
- `board_memo(text)` (published to the log, unscored, diagnostic and decorative)
- `end_turn()`

### 9.2 Context policy (identical for all models)
Fixed system prompt (rules, tone, tool docs), the persistent notes file, the last 2 quarters of briefings and actions, and the current briefing. Older detail is only available through the tools. A model that does not use its notes forgets; that is part of the test.

### 9.3 Information tiers (the "prior" question)
Models get **no numeric prior on loss rates by default**. Reasoning about base rates from sector descriptions and learning from experience is the point.

Needed anchors that aren't priors:
- unit definitions and the scale of the currency
- quarter-1 market quotes are visible through the public rate index (the real-world anchor: you learn the going rate by seeing it)
- the rules of the game, stated fully

Configurable ladder, recorded in the run manifest:
- **Tier 0 (headline)**: rules + unit scale only.
- **Tier 1 (easier)**: Tier 0 plus 8 quarters of anonymised pre-game industry history (average rate, loss ratio).
- **Tier 2 (easiest)**: Tier 1 plus a deliberately imperfect actuarial note.

Scores are only comparable within a tier. Running the same model at Tier 0 and Tier 1 also shows how much it relies on being handed information.

## 10. NPCs

Versioned and scripted. Used in both modes.
- **Actuary-bot**: prices at its running estimate of expected loss plus a fixed margin; updates estimates from its own claims; has reserve discipline. The reference for normalisation.
- **Reckless-bot**: undercuts the market index by 10%, never reserves for IBNR.
- **Cycle-follower**: sets price to last quarter's market average.
- **Predator**: when well capitalised, undercuts the weakest rival to push it out.
- **Random-bot**: random but valid actions. Zero point of the scale.
- **Reinsurer, regulator, guarantee fund**: system actors.

Benchmark-mode line-up (initial): subject + actuary-bot + cycle-follower + reckless-bot + predator. NPCs *react* to market conditions (including the subject's prices) but their rules never change within an `ENV_VERSION`.

## 11. Scoring

Per game:
- **Shareholder value** `V = terminal equity + cumulative dividends - (1 + dilution) x capital injected` (insolvent: `V = 0` and a flat penalty).
- `game_score = ln(V / V0)` with an insolvency floor.
- **Paired score** `Δ = game_score(subject) - game_score(reference bot in the subject's seat on the same seed)`. The reference bot run is cached per `(ENV_VERSION, seed, line-up)`.

Reported per model:
- Mean `Δ` with bootstrap CI over seeds (start with 20 seeds, check the CI width, adjust).
- **Normalised score**: 0 = random-bot, 1 = actuary-bot.
- **Survival rate** and median time-to-ruin.
- **Calibration**: Brier/log score of its 4-quarter-ahead loss-ratio predictions against the realised ratio (rewards good reasoning even when the dice are bad).
- **Failure-mode tags** (automatic): price-war victim (market share gain followed by loss-ratio spike), reserving failure (reported vs true reserve gap), concentration blowup (>40% of exposure on one provider at an event), precedent-lag (quarters between ruling and repricing).
- **Cost**: tokens, dollars, score per dollar.

Competitive: Elo/TrueSkill over lineups, head-to-head matrix, market-behaviour metrics (average price vs actuary-bot, volatility of the rate index, collusion signal when conference is on).

## 12. Token and cost tracking

All model calls pass through one adapter. Log per call: run id, seed, quarter, model id, provider, input/output/cached/reasoning tokens, latency, tool-call count, finish reason, and the **price table snapshot** used. Aggregations: cost per quarter, per game, per model, tokens-per-quarter curve (notes bloat shows up here), score per dollar.

Budget guards: per-run and per-session hard caps; the runner refuses to start a job whose estimated cost exceeds the cap; a kill switch in the UI. Rough estimate for planning: ~20k tokens in and ~3k out per turn, ~0.8M in / 0.12M out per game, ~16M in / 2.4M out for 20 seeds per model **[verify against real runs]**. Lockstep batching of all seeds per quarter through a Batch API is a later optimisation.

## 13. Model roster

- Anthropic (direct API): the current family, from the small model to the flagship.
- Others via OpenRouter (one adapter): current flagship and small model from OpenAI, Google and xAI; one or two strong open-weight models (DeepSeek, Qwen, Kimi).
- Exact model IDs and prices live in `models.yaml`, pinned per run. No IDs hard-coded in the engine.

## 14. Architecture

```
benchmark/
  engine/        # pure Python sim, no network, no LLM; deterministic given seed + actions
  content/       # cached dossiers, headlines, event templates, manifest.json (hash + generator model)
  agents/        # model adapters (anthropic, openrouter), tool schema, context builder
  bots/          # NPC policies
  runner/        # job runner, resume from checkpoint, cost accounting
  analysis/      # scoring, plots
  web/           # control-room API + UI (private)
  site/          # public static site: explainer, stories, results
  models.yaml
  DESIGN.md
```

Principles:
- The engine is a library with a `step(state, actions) -> state, observations` interface and full JSON-serialisable state, so every run can be checkpointed after any quarter and resumed after a crash or a rate-limit stall.
- Every run writes an append-only event log (JSONL) of observations, actions, tool calls, memos, plus the manifest (`ENV_VERSION`, tier, seed, models, prompt hash). Plots are derived from logs, never from live state.

### 14.1 Web control and hosting (Railway)
- **Web service**: FastAPI + a small frontend (HTMX or lightweight React). Start/stop runs, pick model/mode/seeds/tier, see live progress and spend, browse results and replays.
- **Worker service**: pulls jobs from a queue and executes games. Separate from web so a deploy doesn't kill a run. Redis or Postgres-backed queue (Postgres only is simpler: one less service).
- **Postgres**: runs, jobs, call-level token logs, scores, checkpoints. Large logs (JSONL replays) go to a Railway volume or object storage; the container filesystem is ephemeral and must not be the system of record.
- **Secrets**: API keys as Railway env vars, never in the repo.
- **Auth**: required from day one, since the UI can spend real money. Single-user login or a shared secret, plus the budget caps in 12.
- Local-first: the CLI runner works without the web stack, and the web UI wraps it. Develop and tune locally, deploy once the engine is stable.

## 15. Readouts

- Equity **fan charts** per model across seeds (median, 10/90 bands).
- **Underwriting cycle**: market rate index vs cumulative catastrophe losses.
- **Time-to-ruin** survival curves.
- **Market-share stacked area** per game, with insolvencies as collapsing bands.
- **Concentration heatmaps**: book by provider x sector vs where losses landed.
- **Calibration** plots (predicted vs realised loss ratio).
- **Claims-decision Sankey** (pay/settle/contest/deny to outcomes).
- **Precedent timeline** with each model's rate response overlaid.
- **Cost panel**: tokens per quarter, dollars per game, score per dollar.
- **Replay viewer**: one game quarter by quarter, news ticker, memos, the bell.
- **Hall of Infamy**: final board memos of insolvent insurers.

### 15.1 The website

The site is a product in its own right: fun, detail-rich, and readable by someone who has never heard of the benchmark. Three parts, plus a control room.

**A. How it works (explainer).** A substantive, designed, scroll-driven walk through the mechanics: the world and its fictional AI vendors, a sample dossier and how to read it, how clients choose between quotes, why cheap wins and then hurts (winner's curse), reserves and the long tail, the legal system and precedent, reinsurance, the regulator and guarantee fund, the event catalogue. Interactive where it earns its place (e.g. a toy price war you can drive; a slider that shows how reserving too low flatters profit and then explodes). Deadpan house style throughout. Each mechanic links to a real example from a logged run.

**B. Stories (narrative layer).** Auto-extracted, then curated, accounts of interesting runs, told as annotated timelines: the quarter-by-quarter briefing, what the model saw, its tool calls, its notes and board memo, the decision, and what the hidden truth was. Pipeline:
1. A detector flags candidate moments in every run: insolvency, biggest reserving miss, price-war entry and exit, repricing after a precedent (or failure to), a catastrophe response, contested claims that went badly or well, notable notes/memo text, a sudden strategy change, collusion attempts at the conference, predation.
2. Each moment is rendered as a "scene card": context, the model's reasoning excerpt, the decision, the outcome, plus the truth reveal ("what the model could not know").
3. A separate narrator model writes the deadpan commentary from the structured scene data, clearly labelled as machine-written, with the source log linked. Commentary is cached and versioned like other content.
4. Runs get an "interest score" from the detectors; the top ones get full-run storybooks (every decision illustrated), the rest get highlight reels. Every run's complete decision log stays browsable.
Includes the Hall of Infamy and a "Best Quarter" / "Worst Quarter" gallery.

**C. Results (chart-rich).** The complete set of results, one page per level: leaderboard (benchmark mode, per tier), per-model pages (fan charts, survival curve, calibration, failure-mode breakdown, cost), head-to-head and Elo for competitive mode, market-behaviour charts (cycle, share, concentration, herding), and a methods/caveats page with confidence intervals and the `ENV_VERSION` shown prominently. Charts are rendered from the run logs at build time to static JSON and drawn client-side, with hover detail and links back into the relevant story. Consistent, accessible palette and light/dark support.

**D. Control room (private).** Start/stop runs, spend and budget caps, queue, live progress. Behind auth. Not part of the public site.

Delivery: the public site (A–C) is statically generated from the results store, so it is cheap to host and can be published separately from the worker/control room. Build step: `analysis/` exports results and story data as JSON; the site renders from that.

## 16. Build plan

1. **Engine + bots only.** World generation, quoting, client choice, claims, reserves, legal, precedent, events, regulator. Run bot-only markets in bulk.
2. **Calibration.** Targets: (a) actuary-bot survives most seeds but doesn't dominate; (b) reckless-bot does best early then fails in a majority of seeds; (c) an underwriting cycle emerges; (d) catastrophes dominate no more than ~half the variance in `game_score` across seeds, and the paired score cuts that sharply. Tune the **[tune]** values.
3. **Agent layer.** Tool schema, context builder, Anthropic adapter, cost logging. Mini-game: 12 quarters, 2 models.
4. **Benchmark mode run** with the model roster; first leaderboard; look at failure-mode tags.
5. **Competitive mode** and the conference experiments.
6. **Web UI on Railway** (control room first).
7. **Public site**: explainer, story pipeline, results pages. Story detectors can be built earlier, against bot-only logs, since they only need the event log format.
8. **Polish.**

## 17. Risks and open questions

- **Calibration is the project.** If the economy is badly tuned, either the actuary-bot wins trivially or nothing survives. Budget most of the effort here.
- **Dossier leakage**: if dossiers state the hidden risk too clearly the task is reading comprehension; too vaguely, it's noise. Needs a check: how well does an oracle that sees only the dossier text (e.g. a regression on features extracted from it) predict true loss?
- **Prompt sensitivity**: results may move with prompt wording. Prompts are versioned and hashed into the manifest; test two phrasings once.
- **Contamination**: content is procedurally generated per seed, but the mechanics will leak into training data if published. Keep validation seeds private.
- **Safety/tone line**: catastrophe narration stays abstract (no operational detail about how an attack works). Worth a content review of the event templates.
- **Context-policy fairness**: models with larger useful windows are handicapped by the fixed window. This is deliberate for comparability; a "long-context" variant could be added later.
- **Judging pay-offs**: shareholder value with no time discounting rewards late gambling near the end of the game. Consider an end-of-game wind-down rule or a franchise-value term. **[decide before calibration]**

## 18. Agent layer as built (v0)

- **One fresh conversation per quarter.** The model gets the stable system prompt (cached), a structured briefing, and its own notes document. No chat history carries over, so there is nothing to compact and no thinking-block history editing. Persistent memory is `write_notes` (6000-character cap, replaced each time) plus a rolling eight-quarter table in the briefing.
- **Tools** (`agents/tools.py`): `get_applicants` (paged), `submit_quotes`, `set_rate_manual`, `decline`, `decide_claims`, `set_ibnr`, `pay_dividend`, `raise_capital`, `set_reinsurance`, `predict_loss_ratio`, `write_notes`, `board_memo`, `end_turn`. Nothing takes effect until `end_turn`. Undecided claims are paid in full; applicants with no quote and no manual price are declined.
- **Fairness choices.** Same prompt, tools, tool-call cap (25 rounds) and briefing for every model. No sampling parameters. Adaptive thinking where supported, effort only if set in `models.yaml`. **No refusal fallbacks**, because a silent switch to another model mid-game would contaminate the result; refusals are logged and the quarter proceeds with whatever was decided.
- **Information tier 0**: no numeric loss priors in the prompt. The public last-quarter rate on line by sector is in the briefing, which is the only price anchor.
- **Cost control.** Every call logs tokens (input, output, cache read, cache write), latency, tool-call count, request id and a snapshot of the price table to `runs/<run_id>/calls.jsonl`. A per-run `Budget` aborts when the cap is crossed. Decisions, memos, notes and predictions go to `game.jsonl` (the raw material for the story pipeline).
- **Not yet done**: OpenRouter adapter for non-Anthropic models; scoring of `predict_loss_ratio`; parallel seed runner; batch mode.
