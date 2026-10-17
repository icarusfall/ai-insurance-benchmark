# Handover: where the project stands (2026-10-17)

Written so a fresh session (or a reviewer) can pick up cold. Read `README.md` for the pitch, `DESIGN.md` for the spec, `CALIBRATION.md` for what has been tuned and why, and `results/wave1_partial.md` for the first LLM results.

## What exists and works

- **Engine** (`engine/`): deterministic quarterly insurance market. Hidden world (6 fictional AI vendors, 8 sectors, clients with hidden attributes, pre-drawn incidents so insurer actions never change the exogenous world), sealed quotes and softmax client choice, claims with reporting lag, IBNR reserves, pay/settle/deny/contest with hidden liability probability, exogenous precedent rulings, catastrophes, vendor flaws, mandates, a regulator and audit, guarantee fund with levy cap, per-claim excess-of-loss reinsurance from an NPC reinsurer, costly capital raising, dividends.
- **Scripted insurers** (`bots/`): actuary (the yardstick), reckless, cycle-follower, predator, random.
- **Benchmark mode** (`runner/benchmark_mode.py`): subject vs frozen NPCs, scored as a paired difference against the actuary-in-seat reference on the same seed.
- **LLM layer** (`agents/`): system prompt and quarterly briefing, 13 tools, one fresh conversation per quarter with a notes document as memory, adapters for Anthropic (SDK), OpenAI (Responses API, stateless with encrypted reasoning), Gemini (native) and OpenRouter (Chat Completions), per-provider concurrency caps, retry/backoff, fail-fast on config errors, per-call token and cost logging, per-run and per-batch budget caps.
- **Runners**: `runner/play.py` (one game), `runner/batch.py` (parallel, resumable, with one-quarter preflight per model), `runner/report.py` (table), `runner/simulate.py` and `runner/diagnose.py` (bot-only calibration), `runner/check_keys.py`.
- **Tests**: 14 pass (`python -m pytest`). The LLM loop is tested with a scripted fake model; adapter translation is tested with mocked HTTP.

## What is NOT done

- Wave 1 is incomplete (13 of 40 games; see `results/wave1_partial.md`). Resume with the same command; finished games are skipped:
  `python -m runner.batch --models claude-haiku-5-5,gpt-5.6-luna,gpt-5.4-nano,gpt-5-nano,gemini-3.1-flash-lite,gemini-3.5-flash-lite,deepseek/deepseek-v4-flash,qwen/qwen3.5-35b-a3b --seeds 5 --workers 8 --per-game-cap 1.5 --total-cap 15 --out runs/wave1`
- No scoring of `predict_loss_ratio` (calibration); no failure-mode tagger; no story/narrative pipeline; no charts.
- No competitive mode runner (engine supports multiple LLM seats; no orchestration, no Elo).
- No web site or control room (plan in DESIGN.md sections 14.1, 15.1 and 19).
- Higher-tier models (Fable, Sonnet, Opus and equivalents) deliberately not run yet.
- Reinsurance has no capacity limit or counterparty risk; precedent is exogenous; the competitive-mode conference channel is not built.

## Operational facts

- Repo: https://github.com/icarusfall/ai-insurance-benchmark (branch `main`). Check `git status` / `git log origin/main..` for anything unpushed. The owner approves each push explicitly.
- Keys are in `.env` (git-ignored; names in `.env.example`): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`. Never print or commit them. The owner prefers direct provider keys over OpenRouter to avoid its markup.
- `runs/` is git-ignored: raw logs (`calls.jsonl`, `game.jsonl`, `result.json`) exist only locally. `results/` holds committed summaries.
- Prices in `models.yaml` for OpenAI and Gemini are reference figures copied from OpenRouter's listing (2026-10-17), not verified against the providers' pages. OpenRouter calls log their exact cost. Reasoning tokens count as output.
- Gemini direct hits per-minute quota 429s under concurrency; limited to 2 concurrent calls (`agents/limits.py`). `gemini-2.5-flash-lite` is withdrawn for new users.
- Environment version `0.1.0-dev` (`engine/params.py`); any mechanics change should bump it and invalidate comparisons.

## Questions for an expert review (the reason for the pause)

1. **Is the benchmark measuring what it should?** 7 of 13 LLM games ended in ruin where the scripted actuary never did on the same seeds. Is that the intended difficulty, a floor effect that hides differences, or an environment mis-tuned for LLM behaviour (e.g. the regulator and audit mechanics, thin capital relative to variance, 40-quarter horizon)?
2. **Scoring.** Score is ln(value/40) with ruin at value 0. Ruin dominates means and variance. Options: report survival and conditional performance separately; a smoother penalty for near-failure; a risk-adjusted or time-weighted value; handling of dividends (luna paid out most of its equity and survived; Haiku paid out and then failed).
3. **Information design (tier 0).** Models get no numeric priors, only last quarter's public rate on line by sector. First-quarter pricing is therefore blind (gpt-5-nano initially quoted absurdly high premiums). Is that the right anchor? Should there be a pre-game market history, or an explicit loss-ratio statistic?
4. **Statistical design.** Pairing with an actuary reference cut variance by roughly half for competent subjects in bot-only tests, less for poor ones. How many seeds are needed (30? 50?) and is the actuary the right reference? Cost at about $0.25 per game makes 30 seeds x 8 models about $60, but wall time per game is 7 to 46 minutes.
5. **Context policy.** Fresh conversation per quarter, notes capped at 6000 characters, last 8 quarters as a table. Does this help or handicap models? Worth reading the notes files (`game.jsonl`) to see what models actually record and whether they use them.
6. **Fairness and reproducibility.** Reasoning models take no temperature; provider non-determinism means the same (model, seed) can differ. Is one game per (model, seed) enough, or are repeats needed? Prompt sensitivity is untested.
7. **Engine realism versus fun.** Are the stylised economics (premium levels, cat sizes, lags) plausible enough? The dossier explains 82% of log expected loss but only 25% of within-segment risk, so the rest comes from claims experience; is that the right balance?
8. **Tone and safety.** Catastrophe wording stays abstract; board memos are free text. Worth a content review before publishing logs.
9. **Product.** The public site (mechanics explainer, auto-narrated stories from real runs, chart-rich results) and a password-protected control room to launch runs. What is the minimum credible first version?

## Suggested next steps (not yet agreed with the owner)

1. Read a few full `game.jsonl` logs (notes, memos, tool traces) from the ruined games to separate model weakness from environment or prompt problems.
2. Decide on the scoring change before spending more on runs.
3. Resume wave 1 to completion (about $15 cap, 2 to 3 hours), then run the same models on seeds 5 to 29.
4. Only then add the mid and upper tiers, and build the site on top of real results.
