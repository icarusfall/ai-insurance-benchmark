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
