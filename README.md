# Act of God & Co.
### An AI-liability insurance benchmark for language models

> *"Your pharmacy-refill agent dispensed 40,000 Ambien. The vendor says it is working as intended. Please advise on reserves."*

Language models run an insurance company for ten years (40 quarters). The product they sell is **liability cover for businesses that deploy AI agents**. They must price risk from prose descriptions, survive competitors who undercut them, set aside money for claims nobody has reported yet, decide which claims to pay or fight, and keep their nerve when the news turns grim. The world occasionally produces catastrophes. The narration never acknowledges how grim they are.

It is a benchmark in the spirit of Vending-Bench: no trick questions, just a long, boring-looking job where small judgement errors compound for years before they show up.

**Live site:** [ai-insurance-benchmark-production.up.railway.app](https://ai-insurance-benchmark-production.up.railway.app/): how it works, how insurers die, results, a playable version, and [why it exists](https://ai-insurance-benchmark-production.up.railway.app/about.html).

**Status (October 2026):** the engine, scripted rivals, model-agnostic agent layer (Anthropic, OpenAI, Gemini, OpenRouter), batch runner with cost tracking, calibration harness and public site all work. Inexpensive models have run 20 games, with a 60-game wave in progress; larger models are next. An early design review ([`REVIEW.md`](REVIEW.md)) found serious flaws, which were fixed and are logged in [`CALIBRATION.md`](CALIBRATION.md). The tournament mode is not built yet.

**How it was built:** vibe-coded with Claude Code as one of a series of weekly hobby projects. The questions, design decisions and judgement calls are mine; most of the typing is Claude's. A personal project, unconnected with any employer.

---

## Why insurance?

Insurance is a purpose-built test of judgement under uncertainty:

- **You are paid first and pay later.** Premiums arrive now; the claims they cause arrive up to two years later. An insurer that ignores this looks brilliant for two years and then explodes.
- **Cheap wins, then hurts.** The client picks the lowest quote, so whoever most *underestimates* a risk wins it (the winner's curse). Price wars feel great until the claims land.
- **Nobody knows the right price.** There is no standard actuarial table for "autonomous agent built on a flaky foundation model". Models have to reason it out and then adapt as evidence arrives.
- **Disasters are correlated.** Many clients build on the same few foundation models. One bad software update can hit a whole slice of your book at once.
- **The law is still being written.** Courts rule during the game on who is liable when an agent misbehaves, and those rulings reprice the market overnight.

## How a game works

You are one insurer. Each of the 40 quarters goes like this:

```mermaid
flowchart LR
    A[Briefing<br/>news, applicants,<br/>claims, finances] --> B[Decide<br/>quotes, claim decisions,<br/>reserves, reinsurance, dividends]
    B --> C[Market resolves<br/>clients choose,<br/>incidents occur]
    C --> D[Accounts<br/>audit, regulator,<br/>solvency]
    D --> A
```

**1. Applicants arrive.** Each client is described in a short dossier: sector, size, how autonomous its agents are, which foundation-model vendor it uses, and how seriously it takes safety, plus the occasional hint. Some facts are stated, some implied, and some are red herrings ("recently hired a Head of Responsible AI"). The *true* risk is hidden. A few things about every client you can never learn from the dossier.

**2. You quote.** Premium, limit, deductible, and the wording of the policy (for example, excluding catastrophes or upstream-vendor failures). Every insurer quotes in secret at the same time.

**3. Clients choose.** Price matters most, but not only: clients also weigh how broad the cover is, your financial strength and your reputation for paying claims. They can also go without insurance. Renewing clients get a small loyalty bonus for their current insurer.

**4. Bad things happen.** Incidents occur on the policies in force. They are reported to you **1 to 8 quarters later**. Meanwhile you must keep reserves for claims that have happened but have not been reported yet (the "incurred but not reported" reserve). Reserve too little and your accounts look great until they don't.

**5. You handle claims.** Pay, settle for less, deny, or fight in court. Claims are more or less murky. Denying a valid claim can lose you a bad-faith case and your reputation. Fighting is slow and costs legal fees.

**6. A regulator watches.** It audits your reserves and compares your capital with a risk-based requirement, then acts on a graded ladder modelled on US risk-based capital: below one level no dividends, below the next no new business, below the last it takes over. You can call on your shareholders for more capital, but every dollar costs you extra in the final score, so leaving it late is expensive. When an insurer fails, a guarantee fund pays its smaller clients' claims, funded by capped levies on the survivors. (A hidden UK-flavoured variant swaps in Solvency-style capital rules, loser-pays courts and no bad-faith tort: `--regime uk`.)

**7. Repeat for ten years.**

### The world

| Piece | What it does |
|---|---|
| **Six fictional AI vendors** (Gorbly, Yottabrain, Mindful Systems, ChadGPT, ...) | Each has a hidden defect rate. One bad update hits every client built on it. |
| **Eight sectors** (medical, finance, logistics, customer service, ...) | Different claim frequencies and sizes. Court rulings move liability sector by sector. |
| **Catastrophes** | Rare, enormous, and legally unresolved at the time they happen. |
| **Regulation** | Mandatory cover (demand doubles, prices crash), liability safe harbours (claims ease). |
| **False alarms** | Scary headlines, no claims. Punishes overreaction. |
| **Slow drift** | Base rates change quietly over the decade. Punishes never recalibrating. |
| **Reinsurance** | Cover for large claims. Cheap in quiet years; ruinously dear right after a catastrophe. |

The same events, clients and incidents happen in every game that shares a seed, whichever insurer is playing. That is what makes comparisons fair.

## Two ways to play

**Benchmark mode** &mdash; one model against a fixed set of scripted rivals. The environment is frozen and versioned, so a model released next year can be scored against the same world and compared with today's results. The headline score is *paired*: how much better or worse the model does than a reference bot dropped into the same seat on the same seed.

**Competitive mode** &mdash; four models in one market, with scripted rivals around them. This is the fun one: it shows who undercuts whom, who spots a weak rival and goes for the kill, and (with the optional annual conference switched on) who tries to talk the market into raising prices. It produces a ranking rather than a reusable score.

### The scripted rivals

| Bot | Personality |
|---|---|
| **Actuary** | Prices at expected loss plus a margin, learns from its own claims, books reserves properly, doesn't write more than its capital supports. The yardstick. |
| **Reckless** | Undercuts the market, never books reserves for unreported claims, denies murky claims, pays out the "profits". |
| **Cycle-follower** | Copies last quarter's market price. A herd of one. |
| **Predator** | Prices like the actuary, but undercuts hard while healthy when a rival looks weak. |
| **Random** | Valid but arbitrary. Defines the zero point. |

## What gets scored

- **Shareholder value against a hurdle**: final equity plus dividends, less capital injected (with a dilution penalty), each grown at the 2% a quarter shareholders require. The headline ratio R is 1.0 when the insurer earned exactly that; doing nothing scores about 0.67. Insolvency claws back recent dividends.
- **Survival** and time to ruin.
- **Calibration**: each quarter the model predicts its own loss ratio; those predictions are scored, so good reasoning is rewarded even when the dice are unkind.
- **Failure modes**, tagged automatically: price-war victim, reserving failure, concentration blow-up, slow to react to a court ruling.
- **Cost**: tokens and dollars per game, and score per dollar.

Games are run over many seeds because catastrophes are heavy-tailed. Results come with confidence intervals.

## Tone

Deadpan actuarial. Deaths are "casualty units". A pandemic is a "correlated morbidity occurrence". The humour comes from the gap between the language and what it describes, which is how real insurance already works. Each insurer also writes a board memo every quarter; by quarter 30, the memos of the ones going under are the best part.

No real people, companies or attack methods appear. Catastrophes are abstract shocks with a narrative wrapper.

## Try it

```bash
pip install -e ".[dev]"

# run a market of scripted insurers over 20 seeds and print a leaderboard
python -m runner.simulate --seeds 20

# is there an underwriting cycle? how much does the seed matter?
python -m runner.diagnose --seeds 20

# play one real model against the scripted rivals (needs an Anthropic API key; costs money)
python -m runner.play --model claude-haiku-5-5 --seed 0 --quarters 4 --max-cost 1

# tests
python -m pytest
```

Example output (environment 0.3, 20 seeds):

```
bot          score     sd  surv%    value     CR     prem  ruin_q
actuary       0.79   0.43    100    215.3   0.54    328.4     nan
reckless     -1.10   0.92     50     45.9   1.02    249.2    28.4
cycle        -1.90   0.79     40     14.0   1.09    252.6    25.3
predator      0.76   0.44     95    208.1   0.58    309.8    21.0
random       -2.15   0.38     25      3.8   1.29    138.2    26.1
```

Score is ln R. CR is the combined ratio (claims plus expenses over premium; below 1 is profitable). To check that no shortcut strategy beats the reference, run `python -m runner.probe --seeds 20`.

## Models

Direct adapters for **Anthropic**, **OpenAI** and **Google Gemini**, plus **OpenRouter** for everything else (DeepSeek, Qwen, Kimi and so on). Each model is one entry in [`models.yaml`](models.yaml); keys go in a git-ignored `.env` (see `.env.example`). Every call logs tokens (including hidden reasoning tokens) and cost, so score-per-dollar comes for free. Prices in `models.yaml` for OpenAI and Gemini are reference figures; OpenRouter reports its own exact cost per call.

## Repo map

| Path | What's there |
|---|---|
| [`DESIGN.md`](DESIGN.md) | The full specification: mechanics, scoring, architecture, website plan |
| [`CALIBRATION.md`](CALIBRATION.md) | Log of tuning decisions and open questions |
| [`HANDOVER.md`](HANDOVER.md) | Current state, what's missing, and open questions for review |
| [`results/`](results/) | Committed summaries of runs (raw logs stay local in `runs/`) |
| `engine/` | The simulation: world generation, market, claims, regulator. No network access, fully deterministic |
| `bots/` | The scripted insurers |
| `runner/` | Command-line runners and diagnostics |
| `tests/` | Determinism, fairness, agent-loop and adapter tests |
| `agents/` | LLM layer: system prompt and briefing, tool schemas, model adapters, cost and call logging |
| `website/` | The public site (static), its data exporter (`python -m website.build`) and the Blender scripts for its illustrations |
| [`REVIEW.md`](REVIEW.md), [`V0_2_PROPOSAL.md`](V0_2_PROPOSAL.md) | The design review and the changes it led to |

## Roadmap

- [x] Design spec
- [x] Bot-only market engine
- [x] Calibration, with probe strategies that must not beat the reference
- [x] LLM agent layer: tools, context policy, token and cost logging
- [x] Benchmark runs: inexpensive models (one wave complete, one in progress)
- [x] Public site: how it works, how insurers die, results, play it yourself
- [x] Regulatory regimes: US-flavoured headline, hidden UK variant
- [ ] Larger models (mid tier, then a flagship taster)
- [ ] Saturation check: does a stronger model keep scoring higher?
- [ ] Competitive mode: several AI insurers in one market, and whether they drift into tacit price-fixing
- [ ] Control room on Railway

## Honest caveats

- This is a hobby project, built for fun and curiosity rather than publication. Treat results as indicative: samples are small.
- The economy is a model. Its numbers are tuned to make the game interesting, not to predict real-world AI liability.
- Scores are only comparable within the same environment version and information tier.
