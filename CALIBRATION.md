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
| actuary | 70% | 60.7 |
| reckless | 5% | 1.5 |
| cycle | 0% | 0.0 |
| predator | 75% | 61.8 |
| random | 50% | 15.9 |

Start equity is 40, so value above 40 means growth.

## Open calibration questions
- Does an underwriting cycle emerge (rates fall in quiet years, jump after catastrophes)? Not yet checked.
- Random-bot survives half the time; probably too forgiving. Is the market margin too fat, or is adverse selection too weak?
- Cycle-bot never survives (it copies prices with no loss feedback); is that the right behaviour for a herd bot?
- Predator is not distinguishable from the actuary in 20 seeds; its trigger rarely fires.
- Dossier realism: how well do dossier signals predict true loss? (Check regression R^2 before LLM runs.)
- Variance decomposition: share of score variance explained by seed vs. insurer, and how much the paired score removes.
