# Design review (2026-10-17)

An outside-expert pass over the design, the engine and the 13 wave-1 games, written to answer the questions in `HANDOVER.md`. It is based on reading the code and logs and on cheap bot-only probes (no LLM spend). The probe script is reproduced at the end.

**Bottom line:** the plumbing is good, but the benchmark is not yet measuring underwriting skill. Three issues dominate and should be fixed before any more paid runs:

1. **Doing nothing is a strong strategy.** A bot that writes no business scores value 59.6 (+0.40) from interest alone. The actuary's median is about 100, but its seed-to-seed spread (0 to 183) is so wide that at 20 seeds the null bot is not significantly worse (paired delta −0.29, 95% CI [−0.64, +0.26]). gpt-5.6-luna, the "steady survivor" (62 to 66), is in effect the null bot plus a little.
2. **Ruin comes from single risks, not from underwriting judgement.** Policy limits run to 120 (180 is allowed) against starting equity of 40, and nothing caps the net line on a single risk. On seed 1, the same infrastructure client produced a covered claim of about 40 in Q14 for three different LLMs (Haiku's cash fell from 46 to 11 with **one or two policies in force**). Survival comes down mostly to whether reinsurance was bought before the lottery ticket landed. The actuary buys it automatically every quarter; most LLMs did not, or bought it late.
3. **The reference and the NPCs are handed the true model of the world; the subject is handed nothing.** `bots/priors.py` gives every NPC the true functional form, the true severity distribution and near-true coefficients. At tier 0 the paired score therefore measures "distance from a near-oracle", in a market priced by near-oracles, rather than skill given equal information.

Two further findings from the probes (appendix):

4. **The reference is easy to beat by trivial tweaks.** The actuary with a 30% margin instead of 10% beats the reference by +0.42 (CI [+0.12, +0.85]). Dropping its reinsurance gains +0.22 (CI just crosses zero). A reference that simple changes can beat is not near the frontier, so "beats the actuary" is a low bar and a positive delta is easy to misread.
5. **Claim handling has a dominant, dishonest strategy.** Denying every claim beats the reference (+0.18, CI [+0.08, +0.30]); paying every claim, the harness default for undecided claims, loses −0.69.

Everything below is detail, ordered by how much it should change the plan.

---

## 1. Economics: the upside is too small relative to the tail

| Quantity | Value | Source |
|---|---|---|
| Null bot (no business) | 59.6 every seed (+0.40) | `INVEST_RATE` 1%/q on 40 for 40 quarters |
| Actuary value, 20 seeds | median ~101, range 0 to 183 | probe |
| Actuary premium written, seed 3 | ~330 over 10 years (~33/yr vs equity 40) | bot-only game |
| Actuary reinsurance spend, seed 3 | 79, i.e. **24% of premium** | same |
| Largest covered claims, seed 3 | 72, 54, 42, 30 (equity 40) | same |
| Policy limits, seed 3 | median 15, p90 60, p99 120 | same |

What this means:

- **Underwriting profit is roughly the same size as the risk-free return**, so the best response to uncertainty is to write little. That is a legitimate strategy for a real insurer only if capital has a cost; here it doesn't, so idle capital is free.
- **The tail is lethal and only partly diversifiable.** The relevant ratio is net single-risk exposure to capital, not premium to capital. Real insurers keep their net line per risk to low single-digit percentages of surplus, and regulators enforce that. Here a cheap model can take a 120 line on 40 of equity without being told it has done something mad.
- **Reinsurance is the decisive lever and is both underpriced and overpriced.** It is priced at 1.25x the *oracle* expected ceded loss, and that oracle excludes catastrophes, so catastrophe protection is free. But the actuary's standing 10x-attachment layer cedes a quarter of its premium. The whole game is quite sensitive to this one parameter.

Suggested changes (pick a coherent set, then recalibrate):

- **Charge for capital.** Either score excess over the risk-free path (subtract `V0 × 1.01^40`, so the null bot scores 0) or make the investment yield on surplus lower than the yield shareholders demand (e.g. 2%/yr earned, score discounted at 8%/yr). This turns "hoard and survive" from a strong strategy into a zero.
- **Cap net line size.** For example, regulator rule: net retained limit per risk ≤ 10% of audited equity, otherwise restricted, or simply reject such quotes with a tool error that says why. Alternatively scale the world so that the median limit is a few percent of capital (more, smaller clients).
- **Price catastrophes into reinsurance**, and give the reinsurer finite capacity (already in DESIGN.md, not built).
- **Recalibrate to a target**: actuary roughly 1.5 to 2x the null bot in median value, ruin under 10% for a competent bot, and a seed-to-seed spread that 30 seeds can resolve.

## 2. Scoring

Current: `score = ln(max(V,1)/40)`, ruin = −3.69, best observed +0.83.

Problems:

- **The floor is arbitrary and dominates.** Ruin costs about 4.4x the best upside observed. A model ending on value 1 scores the same as ruin. Means and variances are mostly a count of ruins.
- **The zero point is wrong.** "Random bot = 0" in DESIGN.md is not random: `RandomBot` prices from the near-oracle prior with lognormal noise. The natural zero is the null bot.
- **Dividends then ruin scores 0.** Under limited liability, shareholders keep dividends already paid, so ruin should not erase them. As built, the trap is "punish solvency failure", which is fine as a social objective, but say so. A cleaner and more realistic rule is a **clawback**: dividends paid while audited equity was below the regulatory line (or within N quarters of insolvency) are deducted. That targets the "pay out, then explode" trap exactly, and doesn't punish prudent dividends.
- **End-game exploits are small but real:** `_true_unpaid` values claims in court at `p_liable × covered`, without the 10% interest or the bad-faith loading, so contesting or denying everything in the last few quarters is free value.

Recommendation: report a small dashboard, not one number.

1. **Survival rate** (with a Wilson CI) and time to ruin.
2. **Median and mean V/V0** on a linear scale (ruin = 0 naturally; no arbitrary floor), **net of the risk-free path**.
3. **Win rate against the reference** on the same seed (P[V_subject > V_ref]): robust to outliers and to the ruin floor, and easy to explain.
4. A normalised score: 0 = null bot, 1 = actuary, using medians.

Keep log score as a secondary "Kelly" view if you like, but with a floor set at, say, ln(0.1) rather than ln(1/40).

## 3. Information design (tier 0)

- **The reference is not at tier 0.** All NPCs share a near-true prior. So (a) the paired delta mixes "information gap" with "skill", and (b) market prices from Q2 onward are already near-fair, so an LLM that copies the public rate on line gets adversely selected by better-informed rivals (the cycle bot shows this: 35% survival). That is a realistic and interesting test, but it isn't what the README says is being tested. Options: give the subject the same imperfect actuarial note as the NPCs (call that the headline tier); or add a **learning actuary** that starts from flat sector rates and learns only from public data and its own claims, and use it as the tier-0 reference.
- **Q1 is blind, and Q1 matters.** 120 initial clients arrive over Q0 to Q3. Models opened at 6 to 10% rate on line against a fair rate of roughly 1 to 2% (Haiku, Gemini, luna) or with flat terms (gpt-5-nano: limit 10, premium 0.8 for everyone). Overpricing is survivable but selects the worst risks. A pre-game "market history" of 8 quarters (rate on line and industry loss ratio by sector) is cheap and realistic. Make it the default; keep blind tier 0 as a variant.
- **The model cannot see its own experience.** The briefing gives 8 quarters of premium written, claims count, reported amount and paid, but no earned premium, no incurred losses, no loss ratio, no split by sector or vendor, and no development triangle. Claims lag up to 8 quarters, so the window never shows a mature accident year. A real underwriter has all of this. As built, the test is partly "can you keep an actuarial database in 6,000 characters of notes" (median notes length used: 200 to 1,400 characters). Add a `get_experience` tool returning the model's own loss triangle by accident quarter, and earned versus incurred by sector and vendor. It is the model's own data, so it doesn't break tier 0.
- **Insolvency is triggered on a number the model never sees.** Ruin is `audited_eq < 0`, where audited reserves are at least 60% of true unpaid, including claims not yet reported. The briefing shows reported equity (which uses the model's own IBNR) and a rating letter. Show the regulator's solvency ratio explicitly each quarter (as real regulators publish it), or at least the audit adjustment once applied.
- **Reinsurance quotes leak the oracle.** The quote grid is computed from true expected loss on the model's current book, including active vendor-flaw multipliers. A clever model can back out its book's true expected loss, and a price jump reveals a flaw event. Either add noise and lag to the reinsurer's view, or price it from public market experience.

## 4. Claims sub-game: check for dominant strategies

From the engine formulas (`market._decide`, `world.liability_p`), with p = hidden liability probability, mean about 0.67 for ordinary claims:

| Action | Expected cash cost per $1 covered |
|---|---|
| pay | 1.00 |
| contest | 0.03 + 1.10p (cheaper than paying whenever p < 0.88) |
| deny | 0.6 × 1.6p = 0.96p (always cheaper than paying, before reputation) |
| settle at 0.9p | 0.9p (best, if you can estimate p) |

So on cash alone, deny beats pay for every claim. The only brake is reputation (−0.04 per wrongful unsued denial, −0.05 per lost case), and reputation enters choice as `rep_w × rep`, worth about 13% of price at most.

**The probes confirm it** (appendix): an actuary that denies every claim beats the reference by +0.18 (CI [+0.08, +0.30]) with 100% survival. Equally important, an actuary that **pays every claim**, which is what the harness does for any claim a model leaves undecided, loses −0.69 (CI [−1.24, −0.28]) and survives only 90%. So claim handling, not pricing, is one of the biggest score levers, and the honest strategy is the worst one. Gemini 3.5 Flash-Lite paid 54 of 54 claims; Gemini 3.1 Flash-Lite paid 17 of 18. Fixes: make wrongful denial expensive enough that deny-all loses (suit probability rising with claim size, a regulator market-conduct fine, reputation that clients observe as a claims-paid ratio), and make settlement the only route to beat paying in full, and only when the model estimates liability well.

## 5. Statistics and protocol

- **Seed count.** Seed-to-seed spread for the actuary alone runs from 0 to 183. Once scoring and calibration are fixed, re-estimate the SD of the paired metric and do a power calculation; don't pick 30 or 50 in advance. Survival rate is binomial: at 30 seeds a 50% rate has a CI of about ±18 points.
- **Within-seed model noise.** Run 2 repeats on 5 seeds for two models to split the variance into seed and model stochasticity. If model noise is large, one game per (model, seed) is not enough, and the pairing buys less than it seems.
- **Held-out seeds and prompt variants.** Keep validation seeds private. Test one paraphrase of the system prompt on one model before scaling up.
- **Sequential design.** Run all models on 10 seeds, then add seeds only where the CIs overlap. It is cheaper than a fixed grid.
- **Calibration of `predict_loss_ratio`** is already logged. Score it (it rewards reasoning independently of luck), but define the realised value carefully: incurred-to-date on a 4-quarter window is immature at lag up to 8, so either score it with oracle ultimate losses or with a lag.

## 6. Context and agent harness

- **One fresh conversation per quarter plus notes** is a reasonable and fair choice. Its weakness is the missing own-experience tool above, not the reset.
- **The rate manual dominates hand pricing in practice.** The best single game (Gemini 3.1 Flash-Lite, 91.8) never set IBNR, paid every claim, quoted once by hand in 40 quarters and otherwise tuned a rate manual. By the end it had priced infrastructure at 60% rate on line and defence at 30%, which amounts to exiting them. That is a nice finding, but it means the dossier prose is barely used. The tool definition also caps the manual at sector × two signals × red flags; vendor and size are not inputs, so a manual-driven model cannot price vendor concentration.
- **Tell the model about line size and the solvency ratio** in the system prompt, as a real CEO would know it. That is rules, not priors.
- **Log bug:** `own.restricted` is a numpy bool and lands in `game.jsonl` as the string `"False"` through `default=str`, so it is truthy. Any analysis reading the logs will misread it. Cast to `bool` in `market._view`.

## 7. Realism (question 7)

Broadly plausible as a stylised market. The two places it departs most from reality, and in the direction that hurts the benchmark, are the absence of a cost of capital and the absence of a net-line limit. Expense ratio 20% and the claims lags are fine. Investment income on reserves (insurers earn float on held premium and reserves) is modelled only on cash, which is fine.

## 8. What to do next (proposal)

1. Fix the log bug; add a null bot and the claims-exploit bots to `bots/` and to the calibration harness, so they run with every recalibration. (Free.)
2. Decide the economic changes: cost of capital, net-line cap, catastrophe-priced reinsurance. Bump `ENV_VERSION` to 0.2.0. Recalibrate bot-only against explicit targets (section 1).
3. Change scoring to the dashboard in section 2, with the null bot as zero and a dividend clawback.
4. Add `get_experience` and the solvency ratio to the briefing; add 8 quarters of pre-game market history as the default tier.
5. Decide the reference: an informed actuary plus the same note handed to the subject, or a learning actuary at tier 0. Either way, tune its margin and reinsurance until simple variants (margin30, no_reins) no longer beat it, and re-run the exploit bots (deny_all, pay_all) after the claims fix.
6. Then re-run wave 1 (cheap models, 10 seeds), plus 2 repeats on 5 seeds for two models to measure model noise. About $20.

---

## Appendix: probe results (bot-only, 20 seeds, paired against actuary-in-seat)

| subject | paired delta [95% CI] | survival | mean V | median V |
|---|---|---|---|---|
| actuary (reference) | 0 | 100% | 101.6 | 101.4 |
| null (writes nothing) | −0.29 [−0.64, +0.26] | 100% | 59.6 | 59.6 |
| pay_all (the harness default for undecided claims) | **−0.69 [−1.24, −0.28]** | 90% | 72.2 | 68.1 |
| deny_all | **+0.18 [+0.08, +0.30]** | 100% | 130.0 | 107.5 |
| contest_all | −0.09 [−0.32, +0.08] | 100% | 108.5 | 92.8 |
| low_settle (0.9 × implied liability) | +0.06 [−0.02, +0.16] | 100% | 113.3 | 98.8 |
| margin30 (margin 30% instead of 10%) | **+0.42 [+0.12, +0.85]** | 100% | 133.3 | 115.8 |
| no_reins | +0.22 [−0.02, +0.53] | 100% | 116.0 | 119.7 |
| timid (quotes a quarter of applicants) | −0.41 [−1.03, +0.06] | 95% | 68.0 | 67.0 |

Reproduce with `python -m runner.probe --seeds 20` (about 5 minutes; the bots live in `bots/probes.py`). It defines `Null` (no quotes), and actuary variants that change only claim handling (`DenyAll`, `ContestAll`, `LowSettle` at 0.9 × implied liability + 0.03, `PayAll`), only margin (`margin30`), only reinsurance (`no_reins`), or only volume (`timid`, a quarter of applicants).
