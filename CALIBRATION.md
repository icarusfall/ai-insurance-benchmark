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
- **Seed explains about a quarter of score variance** (raw). The reference-in-seat paired score from the design is not implemented yet; the simple same-game difference does not reduce variance, because the whole market responds to who plays.
- Denying claims was too profitable (saves money, rarely punished). Raised bad-faith loading (0.25 to 0.5), denial reputation hit (0.02 to 0.04) and suit probability (0.5 to 0.6).

## Open calibration questions
- Paired score: implement reference-in-seat runs and measure the real variance reduction.
- Random-bot survives half the time; probably still too forgiving.
- Predator is close to the actuary; its trigger rarely fires.
- Dossier realism: how well do dossier signals predict true loss? (Check regression R^2 before LLM runs.)
- Reckless should arguably be the best early performer; check its first-5-year equity against the actuary.
