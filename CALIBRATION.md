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
- **Dossier signal power** (`runner/dossier_check.py`): sector, size and the structured signals explain 82% of the variance of log expected loss, but most of that is sector and size. After removing them, the dossier recovers only 25% of the remaining within-segment risk; the other 75% sits in hidden attributes and shows up only through claims. That leaves real room for skill (flags, adverse selection, learning from experience) without making it impossible.
- Denying claims was too profitable (saves money, rarely punished). Raised bad-faith loading (0.25 to 0.5), denial reputation hit (0.02 to 0.04) and suit probability (0.5 to 0.6).

## Open calibration questions
- Score design: ruin floor dominates variance. Consider capping the penalty, or reporting survival and conditional performance separately.
- Paired score does not reduce variance; decide on seed count (50+?) once per-call cost is known.
- Random-bot survives half the time; probably still too forgiving.
- Predator is close to the actuary; its trigger rarely fires.
- Dossier realism: how well do dossier signals predict true loss? (Check regression R^2 before LLM runs.)
- Reckless should arguably be the best early performer; check its first-5-year equity against the actuary.
