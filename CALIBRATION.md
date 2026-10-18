# Calibration log

Harness: `python -m runner.simulate --seeds 20` (bot-only market: actuary, reckless, cycle, predator, random).

## Engine v0 deviations from DESIGN.md
- **Precedent** is driven by scheduled exogenous rulings, not by contested-claim outcomes (keeps common random numbers intact). Insurer litigation affects only that insurer's payouts and reputation.
- **Reinsurance** is a per-claim excess-of-loss treaty from an NPC reinsurer, priced off oracle expected ceded loss times a multiplier that hardens after market-wide loss spikes. No capacity limit or counterparty risk yet.
- **Guarantee fund** levy is capped at 12% of an insurer's trailing-4q premium per quarter; any shortfall is borne by claimants (`fund_shortfall`). Uncapped, one reckless failure cascaded through the whole market.
- **Accounting** defers acquisition cost (DAC). Without it, writing growth drained equity by 20% of new premium on day one.
- **Regulator audit** forces booked reserves up to 60% of true unpaid incurred (including unreported).

## Changes made so far (all 20 seeds, lineup above)
| Change | Why |
|---|---|
| Start equity 100 to 40 | Equity of 100 dwarfed a 40-60/yr market |
| Catastrophe hit prob and severity cut ~4x | Cats were 5-8x annual market premium |
| Guarantee fund levy cap | Cascade killed every insurer |
| Per-claim XoL reinsurance | Tail claims on small books |
| DAC in accounting | Growth was penalised unrealistically |
| Actuary: margin 10%, event load 25%, capacity cap | Under-priced flaw events; absorbed rivals' orphans beyond capital |

## Current state (20 seeds)
| bot | survive | mean value |
|---|---|---|
| actuary | 85% | 72.6 |
| reckless | 60% | 48.2 |
| cycle | 35% | 12.3 |
| predator | 80% | 63.8 |
| random | 50% | 12.6 |

Start equity is 40, so value above 40 means growth. Ordering is now actuary > predator > reckless > cycle ~ random.

## Findings so far
- **An underwriting cycle emerges.** With uncapped undercutting, market rate adequacy (premium / oracle expected loss; break-even is about 1.25) fell from 1.09 in year 1 to 0.57 by year 4 and recovered to about 1.2 only after most insurers had died. That race to the bottom was too extreme (reckless and cycle bots compounding each other), so reckless now has a price floor (0.75x its own fair price) and cycle blends market and fair price. Adequacy now sits near 0.95 to 1.1 and drifts up as insurers fail; the cycle is milder.
- **Seed explains about a quarter of score variance** (raw).
- **Paired benchmark mode is built** (`runner/benchmark_mode.py`: subject vs actuary-in-seat on the same seed, NPCs actuary/cycle/reckless/predator). It separates the stand-in bots cleanly at 20 seeds (mean delta: random -2.85, cycle -2.78, reckless -1.35, predator -0.18, CIs mostly clear of zero), but it **does not cut the noise**: sd of the delta (about 2.0) is about the same as the raw score sd. Cause: outcomes are close to binary (survive, or hit the ruin floor of -3.7), and the market responds to who plays, so a shared seed does not make the two runs comparable. Practical consequence: expect to need 50+ seeds to separate models that are close, and consider a score that is less dominated by the ruin floor.
- **Capital raising fixed most of the binary-score problem.** The ruin cliff was the cause. With a costly injection mechanic (cap 1x start equity, 25% dilution; the actuary raises when restricted or rating is low), actuary and predator survive 95-100% and the paired design now works for competent subjects: sd of raw score about 1.0 vs sd of paired delta 0.34 to 0.63. With 30 seeds it separates actuary variants that differ only slightly (margin 0.18 vs the 0.10 reference: delta +0.18, CI [+0.07, +0.30]; no event load: -1.29, CI [-1.84, -0.79]). Poor subjects (random, reckless, cycle) still show high delta variance because they die in some seeds and not others; that is signal rather than noise.
- **Dossier signal power** (`runner/dossier_check.py`): sector, size and the structured signals explain 82% of the variance of log expected loss, but most of that is sector and size. After removing them, the dossier recovers only 25% of the remaining within-segment risk; the other 75% sits in hidden attributes and shows up only through claims. That leaves real room for skill (flags, adverse selection, learning from experience) without making it impossible.
- Denying claims was too profitable (saves money, rarely punished). Raised bad-faith loading (0.25 to 0.5), denial reputation hit (0.02 to 0.04) and suit probability (0.5 to 0.6).

## Open calibration questions
- Seed count: 30 seeds resolves differences of about 0.15 in score between competent subjects; decide the final number once per-call cost is known.
- Random-bot survives half the time; probably still too forgiving.
- Predator is close to the actuary; its trigger rarely fires.
- Dossier realism: how well do dossier signals predict true loss? (Check regression R^2 before LLM runs.)
- Reckless should arguably be the best early performer; check its first-5-year equity against the actuary.

## First LLM results (wave 1, partial: 13 of 40 games; see results/wave1_partial.md)
- 7 of 13 games ended in ruin where the scripted actuary survived every one of the same seeds. Per-game cost $0.13 to $0.69; 7 to 46 minutes.
- Failure modes seen in the logs: **dividend-then-collapse** (Haiku 5.5 paid 15, 3 and 17 in dividends and failed in two of three games), **slow bleed without raising capital** (gpt-5.4-nano, never called `raise_capital`, insolvent at Q22-23 on both seeds), absurd first-quarter prices (gpt-5-nano), and Qwen3.5-35B ruined at Q10 and Q24.
- Steady survivors: gpt-5.6-luna (value 62-66, paid out most equity as dividends); best single game gemini-3.1-flash-lite (91.8).
- Open: whether this much ruin is the intended difficulty or a mis-tuned environment/score; see HANDOVER.md questions 1-3.
- Operational lessons: OpenAI's newer models need the Responses API for tools with reasoning; Gemini quota 429s under concurrency; the first attempt silently produced 40 empty quarters because adapter errors were swallowed (now fail-fast plus a preflight).

## Environment v0.2.0-dev (2026-10-17)

Changes from v0.1 (rationale in `REVIEW.md`, spec in `V0_2_PROPOSAL.md`): value compounds dividends and injections at a 2%/quarter hurdle and the headline ratio is R = value / (40 x 1.02^40); dividends within 8 quarters of insolvency are clawed back; log score floor ln(0.1). Ideal limits 6 per size unit (was 15), no limit above ideal, and a single-risk rule (net retained limit <= 25% of audited equity, else the quote is void). Catastrophe severity kept at its v0.1 absolute size. The reinsurer prices catastrophes, sees vendor flaws a quarter late and carries 15% lognormal noise. Claims: suit after denial 0.8, bad-faith loading 1.0, contest fee 10%, rejected-settlement fee 5%; claims in court valued at end with their loadings. Bots size limits to the line rule; the actuary buys a treaty attaching at its net line cap, pays out reported equity above 2 x K_REG x npw4 + 10 each year-end, and its margin was swept.

Margin sweep (20 seeds; the NPC actuary, the predator and the reference all use margin m; delta of m-0.1 and m+0.1 against m):

| m | reference median R | m-0.1 | m+0.1 |
|---|---|---|---|
| 0.20 | 1.55 | -0.34 [-0.61, -0.10] | +0.13 [+0.07, +0.19] |
| 0.30 | 1.79 | -0.08 [-0.20, +0.05] | +0.02 [-0.09, +0.13] |
| 0.40 | 1.95 | +0.05 [-0.02, +0.13] | -0.05 [-0.16, +0.07] |
| 0.50 | 2.47 | +0.07 [-0.02, +0.17] | -0.23 [-0.35, -0.12] |

The best response sits near 0.35 to 0.40, so the reference margin is set to 0.35.

Probes at margin 0.35 (`python -m runner.probe --seeds 20`), paired delta in ln R:

| probe | v0.1 | v0.2 | v0.2 P(beat ref) |
|---|---|---|---|
| null | -0.29 [-0.64, +0.26] | **-1.20 [-1.35, -1.04]** | 0% |
| pay_all | -0.69 [-1.24, -0.28] | -0.00 [-0.12, +0.12] | 50% |
| deny_all | +0.18 [+0.08, +0.30] | **-0.34 [-0.46, -0.20]** | 10% |
| contest_all | -0.09 [-0.32, +0.08] | -0.10 [-0.18, -0.02] | 30% |
| low_settle | +0.06 [-0.02, +0.16] | -0.07 [-0.16, +0.03] | 30% |
| margin_up (+0.10) | +0.42 (margin30) | +0.01 [-0.12, +0.14] | 40% |
| margin_down (-0.10) | n/a | -0.11 [-0.31, +0.07] | 40% |
| no_reins | +0.22 [-0.02, +0.53] | **-0.32 [-0.47, -0.19]** | 10% |
| timid | -0.41 [-1.03, +0.06] | -0.50 [-0.63, -0.38] | 5% |

Bot-only market (`python -m runner.simulate --seeds 20`):

| bot | survive | mean value | combined ratio |
|---|---|---|---|
| actuary | 100% | 215.0 | 0.54 |
| predator | 95% | 163.5 | 0.58 |
| reckless | 55% | 29.0 | 1.03 |
| cycle | 45% | 16.9 | 1.12 |
| random | 30% | 5.9 | 1.26 |

Against the targets:
- Met: null bot well below the actuary (R 0.67); actuary survival 100%; no probe beats the reference; paired CIs about ±0.13 at 20 seeds (so 30 seeds resolves roughly 0.1).
- Missed: **the market is too profitable.** Reference median R is about 1.9 (target 1.2 to 1.6) and the actuary's combined ratio is 0.54. The equilibrium margin is high because clients will pay well above expected loss (the self-insure option compares against perceived cost and price sensitivity is moderate).
- Missed: **reckless is no longer the early star.** At Q20 its median equity plus dividends is 30 against the actuary's 87. Denying claims is now expensive and, without reinsurance, its limits are capped at its net line.
- Side effect: **claims skill earns little.** pay_all now ties the reference and low_settle is slightly below it. No shortcut wins, but careful settlement does not win either.

## Environment v0.2.1-dev (2026-10-18)

Model-facing fixes only; no scored mechanics or bot inputs changed, so the v0.2 calibration and probe results stand. (1) The briefing's solvency ratio is now the one the regulator computed at the last audit, so a restricted insurer always sees a ratio below 1 (in wave 2 it was recomputed on the next quarter's window, and Haiku was shown 9.1 while restricted). (2) Dossiers say "an enormous" rather than "a enormous". Wave 2 remains the v0.2.0 baseline.

## Environment v0.3.0-dev (2026-10-18): regulatory regimes

Headline rules are US-flavoured: required capital = sqrt((0.22 P)^2 + (0.30 R)^2) (P trailing-4q premium, R audited reserves, floor 1.0); capital ratio = audited equity / required; ladder after US RBC action levels (below 2.0 no dividends, below 1.5 no new business, below 0.7 regulator takes over = insolvent). Dividends: ordinary up to max(10% of equity, last 4 quarters' income) per 4 quarters; more only if the ratio stays at least 3.0. Guarantee levies capped at 2% of trailing premium a year (was 12% a quarter); the fund covers only clients up to mid-sized. The scripted actuary raises capital when its ratio nears the restriction level.

Hidden UK preset (`--regime uk`, version suffix `+uk`): standard-formula-style SCR (3 x sqrt((0.14P)^2 + (0.11R)^2 + correlation 0.5)); no dividends below 1.3; restriction after two audits below 1.0; takeover below 0.35 (MCR); late-payment damages of 15% instead of a bad-faith award; loser pays (claimant costs 15% when the insurer loses, 60% fee recovery when it wins); interest 8%; awards 0.8x; precedent shifts 0.7x; compensation scheme pays 90% for the smallest clients only.

Probes, 20 seeds (paired delta in ln R):

| probe | US v0.3 | UK v0.3 |
|---|---|---|
| null | -1.25 | -0.99 |
| liquidate | -0.89 | -0.62 |
| pay_all | -0.07 [-0.19, +0.05] | +0.01 [-0.07, +0.10] |
| deny_all | -0.36 [-0.53, -0.21] | -0.01 [-0.08, +0.06] |
| contest_all | -0.12 | -0.15 |
| low_settle | -0.14 | -0.08 |
| margin_up | -0.01 [-0.10, +0.08] | -0.06 |
| margin_down | -0.16 | -0.07 |
| no_reins | -0.31 | -0.32 |
| timid | -0.52 | -0.39 |

No probe beats the reference with a CI clear of zero in either regime. Reference median value: US 201 (R about 2.3), UK 154 (R about 1.75; capital is costlier). Under UK rules denial is about free (no bad-faith tort), which matches the real regime's reliance on conduct regulation rather than litigation; a conduct fine for systematic wrongful denial would be the lever if that is unwanted.

US bot-only market, 20 seeds: actuary 100% survival, value 215; predator 95%, 208; reckless 50%, 46; cycle 40%, 14; random 25%, 4.
