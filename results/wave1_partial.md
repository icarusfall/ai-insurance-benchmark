# Wave 1 (partial): cheap-tier models, benchmark mode, seeds 0-4

**Status: stopped by the owner after 13 of 40 games. Treat as anecdote, not a leaderboard.** n is 1 to 3 per model; the confidence intervals are meaningless at this size. The batch resumes from the completed games (`python -m runner.batch ... --out runs/wave1`; `runs/` is git-ignored, so the raw logs live only on the owner's machine; the log and summary table are copied into this folder).

Setup: subject LLM in seat 0 against frozen NPCs (actuary, cycle, reckless, predator); 40 quarters; start equity 40; information tier 0; environment `0.1.0-dev`. Reference = actuary-bot in the subject's seat on the same seed (survived all of seeds 0-4). Score = ln(value / 40) with ruin = value 0 (score -3.69).

| model | seed | score | value | ruin quarter | injected | dividends | cost | wall |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 0 | +0.30 | 54.0 | - | 0 | 15.0 | $0.38 | 20 min |
| claude-haiku-5-5 | 1 | -3.69 | 0 | 31 | 0 | 3.0 | $0.29 | 21 min |
| claude-haiku-5-5 | 2 | -3.69 | 0 | 26 | 3.0 | 17.0 | $0.20 | 14 min |
| gemini-3.1-flash-lite | 0 | +0.83 | 91.8 | - | 0 | 0 | $0.27 | 20 min |
| gpt-5-nano | 0 | +0.59 | 72.4 | - | 40.0 (max) | 0 | $0.19 | 41 min |
| gpt-5-nano | 1 | -1.85 | 6.3 | - | 0 | 0 | $0.20 | 41 min |
| gpt-5.4-nano | 0 | -3.69 | 0 | 22 | 0 | 0 | $0.13 | 7 min |
| gpt-5.4-nano | 1 | -3.69 | 0 | 23 | 0 | 0 | $0.14 | 7 min |
| gpt-5.6-luna | 0 | +0.44 | 62.0 | - | 0 | 16.0 | $0.24 | 13 min |
| gpt-5.6-luna | 1 | +0.51 | 66.4 | - | 0 | 54.5 | $0.26 | 13 min |
| gpt-5.6-luna | 2 | +0.46 | 63.6 | - | 0 | 50.5 | $0.25 | 14 min |
| qwen/qwen3.5-35b-a3b | 0 | -3.69 | 0 | 24 | 20.0 | 0 | $0.69 | 46 min |
| qwen/qwen3.5-35b-a3b | 1 | -3.69 | 0 | 10 | 0 | 0 | $0.21 | 10 min |

Not yet run in wave 1: gpt-5.6-luna seeds 3-4, gemini-3.1-flash-lite seeds 1-4, gemini-3.5-flash-lite (all, the first attempt hit Gemini quota 429s and was discarded), deepseek/deepseek-v4-flash (all), most others' later seeds.

## Observations (all tentative)

- **Cost is small.** $0.13 to $0.69 per 40-quarter game for these models; about 2M input tokens (most cached) and 0.04 to 0.4M output per game. Wall time 7 to 46 minutes per game, dominated by model latency (gpt-5-nano and Qwen are slow).
- **The designed traps are real.** Haiku paid dividends (15, 3 and 17) and then went insolvent in two of three games ("report profits, pay out, then explode"). gpt-5.4-nano bled equity from 40 to about 1 over 22 quarters through under-pricing and rising reserves, and never called `raise_capital` even after the regulator restricted it from writing ("leave it too late").
- **Different strategies.** gpt-5.6-luna was steady and paid out most of its equity as dividends (50+) while surviving; gemini-3.1-flash-lite had the best single result; gpt-5-nano used the full capital injection on seed 0 and still came out positive.
- **Floor effect.** Ruin scores -3.69 and dominates the averages; 7 of 13 games ended in ruin against the actuary reference's 100% survival on the same seeds. Either the task is hard in the intended way or the environment is mis-tuned against LLMs; this needs an expert look (see HANDOVER.md).
- **Reliability.** No adapter errors, refusals or unended quarters in the kept games (Qwen: 2 unended quarters in the report).
