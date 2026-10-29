# Pilot games, environment v0.3 (2026-10-18)

One game each, seed 0, to measure real cost and time per game before committing seeds. Reference actuary on seed 0: R 3.62 (a generous world). One game says almost nothing about rank.

| Model | R | $ per game | Minutes | Calls | Note |
|---|---|---|---|---|---|
| claude-opus-5-5 | 2.82 | 4.46 | 16 | 104 | re-run after the first attempt ran out of API credit at quarter 25 ($3.21 lost) |
| gemini-3.5-flash | 2.16 | 7.29 | 35 | 477 | best non-Anthropic result; far more expensive than estimated |
| gpt-5.6-terra | 1.01 | 3.00 | 18 | 154 | |
| claude-sonnet-5-5 | 0.57 | 1.38 | 9 | 50 | insolvent at quarter 20 |
| moonshotai/kimi-k2.6 | 1.74 | 4.95 | 193 | | needed reasoning effort "medium" to play at all |

## Two surprises worth remembering

**Gemini 3.5 Flash was too expensive, not because of its price per token but because of how it works.** It made 477 model calls in one game (Opus: 104), taking many small tool steps and re-reading the growing conversation each time: about 2.0M uncached and 7.9M cached input tokens, and 352k output tokens of which 311k were hidden reasoning. At $7.29 a game it costs more than Opus here, so it was dropped from the main run. Estimating cost from list prices alone missed this; only a pilot shows it.

**Kimi K2.6 was too slow.** At default reasoning effort it spent its whole 16k-token output allowance on hidden reasoning without ever calling a tool, twice in its first quarter (one call took over 8 minutes), and failed the preflight. At "medium" effort it plays, but still hit the output limit 20 times in its first 21 quarters, with calls of up to 4 minutes: its one game took 3 hours 13 minutes and cost $4.95, more than Terra. It was dropped from the main run. Its effort setting is the one exception to "same settings for every model" and is recorded in `models.yaml`.

## What went into the main run (wave 4)

The cheap four (Haiku 5.5, GPT-5.6 Luna, Gemini 3.1 Flash-Lite, DeepSeek V4 Flash) and Sonnet 5.5 and GPT-5.6 Terra to 10 seeds, Opus 5.5 to 5 seeds, all on v0.3, within about $80. The pilot games count as seed 0.

## Bookkeeping

- A preflight of Kimi at medium effort ($0.09) is missing from the automatic spend tally: its log was deleted by mistake.
- The aborted Opus game ($3.21) is kept in `runs/pilot03/claude-opus-5-5/s0_failed_credit` so the tally counts it.

# Wave 5 pilots, environment v0.3 (2026-10-28)

Newer models, one game each on seed 0, harness 0.3.1 (adds the loop breaker: a quarter ends once a model repeats the identical tool call five times in a row). Same worlds and rules as wave 4.

| Model | R | $ per game | Minutes | Note |
|---|---|---|---|---|
| gpt-6.1-sol | 2.66 | 3.37 | 36 | taken to 10 seeds |
| gpt-6.1-terra | 2.51 | 1.18 | | best value pilot; not yet run in full |
| gemini-4-argon | 1.06 | 2.48 | 29 | taken to 10 seeds |
| x-ai/grok-4.7 | 0.94 | 8.29 | 155 | too expensive |
| gpt-6-luna | 0.90 | 0.13 | | taken to 10 seeds |
| gemini-3.8-flash | 0.86 | 4.71 | 92 | 464 calls; too expensive for its score |
| deepseek/deepseek-v4.1-flash | 0.64 | 0.41 | 46 | insolvent; 25 replies cut off at the output limit, 2 loop breaks; taken to 10 seeds anyway (cheap) |
| minimax/minimax-m3.1-flash | 0.32 | 0.45 | 51 | insolvent; 33 replies cut off, 15 unended quarters |
| z-ai/glm-5.3-flashx | 0.22 | 0.79 | 47 | insolvent; 9 replies cut off |
| qwen/qwen3.8-max-0902 | | 4.71 | 215 | incomplete: connection dropped at Q14, projecting $13.46 a game; dropped |
| mistralai/mistral-large-4-0 | | | | stopped early: projecting $6.45 a game with output-limit hits |

## Lessons

- **Qwen's first attempt exposed a bug**: a reasoning-only reply comes back with `content: null`, and strict providers reject that when it is sent back. The adapter now sends an empty string (commit 7493d29). The failed attempt is kept in `runs/wave5/qwen_qwen3.8-max-0902/s0_failed_null_content`.
- **Projections at quarter 5 understate cost**, especially for Opus: games get dearer as they go. Opus seeds 5, 8 and 9 hit their caps on the first try ($12 lost, kept as `s*_capped`) and were re-run with an $8 per-game cap. Grok went from $6.47 projected at Q5 to $8.29.
- **The 16k output limit hurts some OpenRouter models** (MiniMax, GLM, Mistral, DeepSeek V4.1). It was kept so results stay comparable with wave 4.

## Bookkeeping

- DeepSeek V4 Flash seed 8 (incomplete in wave 4 after a dropped connection) was re-run in `runs/wave4`; the failed attempt is kept as `s8_failed_chunked`.
- GPT-6 Luna seed 1 died on an OpenAI HTTP 520 at Q10 (`s1_failed_520`); DeepSeek V4.1 Flash seed 9 hit its batch cap (`s9_capped`). Both were re-run.
- The loop breaker fired only for DeepSeek: in 7 of DeepSeek V4.1 Flash's 10 games and in the re-run DeepSeek V4 Flash seed 8. DeepSeek V4 Flash's other nine games were played without it.
- Spend to date across all runs after wave 5: $244.88.
