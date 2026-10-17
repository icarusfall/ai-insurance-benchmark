# Environment v0.2: proposed changes (for approval)

Status: **proposal only, nothing applied.** Each block below is independent and can be approved, changed or rejected on its own. After approval: bump `ENV_VERSION` to `0.2.0`, implement, then recalibrate bot-only until the targets at the end are met (`python -m runner.probe --seeds 20` plus `runner.simulate`). Rationale for each block is in `REVIEW.md`.

Numbers marked ✓ were checked with a quick in-memory what-if (10 seeds); the rest are starting points for calibration, not final values.

## A. Scoring: charge for capital (REVIEW 1, 2)

| | v0.1 | v0.2 proposal |
|---|---|---|
| Value | terminal equity + dividends − 1.25 × injected | same items, but each dividend and injection **compounded at a hurdle rate** h from the quarter it happened to the end |
| Hurdle h | none | **2% per quarter** (about 8%/yr; shareholders' required return) |
| Investment yield | 1%/q | unchanged (1%/q, below the hurdle, so idle capital costs money) |
| Headline ratio | ln(max(V,1)/40) | **R = V / (40 × 1.02^40)**, so 1.0 = earned the hurdle |
| Null bot | +0.40 (59.6) | R = (1.01/1.02)^40 = **0.67** by construction |
| Ruin | V = 0 | V = dividends paid **more than 8 quarters before insolvency**, compounded (limited liability with a clawback window); terminal equity 0 |
| Log view | floor ln(1/40) = −3.69 | ln(R) with floor **ln(0.1)** = −2.30, secondary only |

Reported per model (dashboard, not one number): survival rate with Wilson CI; median and mean R; P(R_subject > R_reference) on the same seed; normalised score (median R, 0 = null bot, 1 = actuary); log view.

Knock-on effects: dividends become useful (returning excess capital beats holding it at 1%), which creates real tension with solvency. The actuary needs a dividend rule: pay out reported equity above `2 × K_REG × npw4 + 10` each year-end.

## B. Single-risk exposure (REVIEW 1)

| | v0.1 | v0.2 proposal |
|---|---|---|
| `IDEAL_LIMIT_PER_SIZE` | 15 (limits 7.5 / 15 / 30 / 60 / 120) | **6** (limits 3 / 6 / 12 / 24 / 48) |
| Max quoted limit | 1.5 × ideal | **1.0 × ideal** |
| Net line rule (new) | none | net retained limit per risk (limit minus the reinsurance layer above the attachment) **≤ 25% of audited equity** at binding; otherwise the quote is void and `submit_quotes` / `end_turn` say why |
| Prompt | silent | the rule is stated in the system prompt and the current maximum net line is printed in the briefing |

With equity 40 that is a net line of 10: sizes 0 to 2 fit without reinsurance, sizes 3 and 4 need it. Reinsurance becomes a sizing decision rather than a lottery ticket. Premium levels fall a little (the upper layers carry little expected loss), so check market premium against capital in calibration.

## C. Reinsurance (REVIEW 1, 3)

| | v0.1 | v0.2 proposal |
|---|---|---|
| Catastrophes in ceded price | excluded (free cat cover) | **included**: expected cat ceded loss at the long-run cat rate |
| Price basis | oracle expected loss on the current book, live flaw multipliers | oracle × **lognormal noise (σ 0.15, own RNG stream)**, flaw multipliers **lagged one quarter** |
| Load `REINS_BASE_LOAD` | 1.25 | 1.25 (recheck after the line cap) |
| Actuary treaty | attach 0.12 × equity, limit 10 × attach | **attach = net line cap**, limit = largest limit − attach (buys only what the rule needs) |

## D. Claims (REVIEW 4)

| | v0.1 | v0.2 proposal |
|---|---|---|
| `SUE_PROB_AFTER_DENIAL` | 0.6 | **0.8** ✓ |
| `BAD_FAITH_LOADING` | 0.5 | **1.0** ✓ |
| Contest fee | 3% of covered | **10%** ✓ |
| Fee when a settlement offer is rejected | 2% | **5%** ✓ |
| End-of-game value of claims in court | p × covered | p × covered × (1 + interest + bad-faith loading if denied), plus remaining fees (closes the end-game exploit) |
| Undecided claims | paid in full | unchanged (realistic; inattention should cost money), but the briefing shows "claims you have not decided will be paid in full: N, $X" |

What-if check, 10 seeds, these four constants only (paired delta vs actuary, 95% CI):

| probe | v0.1 (20 seeds) | v0.2 claims what-if (10 seeds) |
|---|---|---|
| deny_all | +0.18 [+0.08, +0.30] | **−1.11 [−1.89, −0.50]** |
| contest_all | −0.09 [−0.32, +0.08] | **−0.51 [−1.24, −0.09]** |
| low_settle | +0.06 [−0.02, +0.16] | −0.07 [−0.24, +0.06] |
| pay_all | −0.69 [−1.24, −0.28] | −0.67 [−1.39, −0.21] |

The shortcuts now lose; settling near the court's view stays the best policy, which is the skill we want to reward.

## E. The reference actuary (REVIEW 3, probes)

- **Margin:** sweep 0.10 to 0.40 in the v0.2 world and set the reference to the best-scoring margin, so that `margin30`-style tweaks no longer beat it. (In v0.1, 30% beat 10% by +0.42.)
- **Reinsurance:** the rule in C.
- **Dividends:** the rule in A.
- **Information:** your call (question 1 below).

## F. Agent layer (REVIEW 3, 6): no parameter changes, but part of v0.2

1. Briefing: the **solvency ratio** the regulator uses (audited equity / (K_REG × npw4)) and the audit adjustment when one is applied.
2. New tool **`get_experience`**: the model's own loss triangle by accident quarter, and earned premium vs incurred losses by sector and by vendor.
3. **Pre-game market history**: 8 quarters of industry rate on line and loss ratio by sector, generated by running the NPC market for 8 warm-up quarters before Q1. Default tier; blind start kept as a variant.
4. Rate manual gains optional **vendor multipliers**.

## Calibration targets (bot-only, 20 seeds, standard lineup)

| Target | Why |
|---|---|
| Null bot R = 0.67 (by construction) | zero point |
| Actuary: survival ≥ 95%, median R between 1.2 and 1.6 | underwriting skill clearly pays, but not trivially |
| No probe beats the actuary with a CI clear of zero (deny_all, contest_all, low_settle, margin30, no_reins) | the reference is locally optimal and the shortcuts don't pay |
| Reckless: best R of all bots at Q20, ruin in ≥ 50% of seeds | the "looks great, then explodes" trap still exists |
| SD of the paired metric small enough that 30 seeds resolve a difference of 0.15 in median R | affordable seed count |

## Questions for you

1. **Reference information.** (a) Keep NPCs on the near-true prior and give the subject the same imperfect actuarial note (headline tier = equal information); or (b) build a learning actuary that starts from flat rates, as the tier-0 reference. My recommendation: **(a) now**, (b) later as an experiment. It is far less work and makes the delta mean "skill given equal information".
2. **Hurdle rate**: 2% per quarter, or something else?
3. **Net line**: 25% of audited equity (lenient, game-like) or 10% (realistic, makes reinsurance near-mandatory)?
4. **Clawback window**: 8 quarters before insolvency?
