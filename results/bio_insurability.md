# Is AI-assisted bio risk insurable?

A toy model taken out for a walk, not a price. Generated tables below come from `python -m catmodel.insurability`
(the bio peril alone, parameters in `catmodel/defaults.yaml`, sources in `catmodel/sources/`). The findings above
them are written by hand from those tables; rerun and reread if the parameters change. 2026-10-29.

## Findings

1. **As a whole, it is uninsurable in the strict sense.** Both pandemic tail fits we found (Marani et al.,
   Cirillo and Taleb) put the tail index below 1, so expected harm has no finite mean. Capped at world GDP, the
   expected harm per event is still set by wherever you put the cap ($2.9tn, $7.2tn, $16.3tn for caps of $10tn,
   $100tn, $1,000tn). That makes it a definition problem, not a pricing problem. If the lognormal reading
   (Corral) is right instead, this test passes; the rest of the findings barely change.
2. **A capped slice is insurable, and cheap.** $1bn of cover per lab costs about $7m a year in expected claims
   across five labs and a premium of about $24m per lab, 0.24% of a $10bn revenue. That is the AIUC essay's claim,
   and it holds up.
3. **But the slice compensates almost nobody.** It pays about 2% of the liability courts would attribute to labs
   and about 0.02% of the harm. Covering half the attributed liability needs about $75bn per lab per event.
   That is beyond any private pool: Price-Anderson's whole scheme is about $15.5bn per incident, and TRIA caps
   the US government's share at $100bn.
4. **Limits turn a tail problem into a frequency problem.** Once limits bind, the tail index hardly affects
   what the mutual pays. The price uncertainty is all in the rate: expected claims span 36× across the sources'
   range. For pricing, the most valuable research is how often AI materially helps cause a catastrophe, not how
   fat the tail is.
5. **The legal regime decides who carries it, not whether the mutual pays.** Moving from "misuse is a
   superseding cause" (2% attributed) to a strict-liability statute (20%) multiplies the labs' liability by 10.
   The mutual's claims stay the same, because the $1bn limit binds either way. The extra lands on the labs'
   balance sheets, uninsured.
6. **Solvency II's 1-in-200 standard sits right on a 1-in-200 peril.** A claim occurs in about 0.5% of years, so
   the 99.5% VaR, and with it the SCR and the capital charge in the premium, flips between about zero and the
   full limit as the rate moves. A tail measure (TVaR, as in the Swiss Solvency Test) or a higher quantile is the
   honest choice for this peril.
7. **Wrong-way risk is real but small at these sizes.** With $10bn per lab, assume invested capital falls 30% and
   members can pay only half a call in the catastrophe year. Unpaid years then go from none to 0.02%. The capital
   that backs a pandemic cover should not itself fall in a pandemic, and the callable part should come from
   someone other than the labs.
8. **Moral hazard is the open question, and it is the essay's thesis.** If the mutual's conditions really cut
   AI-enabled bio risk by the two thirds FRI's experts expect from safeguards, the rate falls back towards the
   baseline. That is worth far more than any premium.

**Verdict.** "Uninsurable" means four specific failures: no finite mean (1), a price uncertain by more than 10×
(3), compensation that is a rounding error (4), and liability undefined in law (8). A capped slice passes on
price, affordability and capital (2, 5, 6). So bio risk can be held as a small, incentive-bearing slice, which is
what the essay asks for, but it cannot be insured as compensation. Anything beyond a token slice needs a government
layer and a liability statute.

**Caveats.** The rate comes from one expert elicitation (FRI). The attribution shares are judgement until the legal
sourcing is done. The epidemic tail fits measure deaths or intensity, not dollars of harm. Every threshold in the
tests is ours.

<!-- generated:start -->

## Tests (bio peril alone, central parameters)

| Criterion | Test | Result | Verdict | What would make it pass |
|---|---|---|---|---|
| 1. Finite expected loss | Tail index above 1, so the mean exists without an arbitrary cap | α = 0.7. Mean harm per event is $2,901bn, $7,244bn, $16,331bn with the cap at $10tn, $100tn, $1,000tn: it grows with the cap. At α = 1.4: $2,194bn, $2,950bn, $3,279bn. | **Fail** | Nothing an insurer controls. Either the lognormal reading of pandemic data is right (Corral), or the risk is only ever covered as a capped slice. |
| 2. A capped slice has a finite price | Expected annual claims on $1bn per member are finite and stable | Expected claims $7.3m a year; mean ground-up harm $42bn a year. | **Pass** | Already passes: limits turn a tail problem into a frequency problem. |
| 3. The price can be estimated | Expected claims vary by less than 10× across the sources' range | $1.1m (optimistic) to $37.5m (pessimistic): 36×. | **Fail** | Narrow the rate: better uplift studies and safeguard evidence (FRI's experts' interquartile range spans 0.01% to 2%). The tail index barely matters once limits bind. |
| 4. Compensation is meaningful | The mutual pays at least 10% of the harm attributed to labs | It pays 1.8% of attributed liability and 0.018% of all harm. Covering half the attributed liability needs a per-event limit of about $75bn. | **Fail** | Limits in the hundreds of billions, which only a government layer could provide (Price-Anderson's whole scheme is about $15.5bn). |
| 5. Premium is affordable | Premium per member below 2% of revenue | $23.7m per member, 0.24% of a $10bn revenue (pessimistic: 8.7%). | **Pass** | Passes at the central case because the slice is small; fails if revenue is low and the rate high. |
| 6. Capital is adequate | Solvency II ratio at least 100% with paid-in capital and member calls | SCR $992.7m against $5.00bn paid in: ratio 554%. But a claim happens in 0.54% of years, right at the 1-in-200 standard, so the 99.5% VaR is either about zero or about the full limit depending on the rate; TVaR 99.5% is $1.36bn. | **Pass** | Passes while limits stay at $1bn per member; the SCR scales with the limits, not the tail. A tail measure (TVaR, as the Swiss Solvency Test uses) avoids the knife edge. |
| 7. Losses are not wrong-way | The chance claims go unpaid does not rise when assets and members are hit too | With $10bn per member, $20bn paid in and $10bn callable from each member: unpaid in 0.000% of years, 0.020% if invested capital falls 30% and members can pay only 50% of a call in a catastrophe year. (At $1bn per member claims cannot outrun capital.) | **Fail** | Hold capital in assets that don't fall in a pandemic, and get callable capital from parties that aren't the members (reinsurers, cat bond investors, government). |
| 8. Liability is legally defined | Attribution is set by law, not a coin toss between legal theories | Labs' expected insurable liability is $415.9m a year if courts treat misuse as a superseding cause (2% attributed) and $4.16bn under a strict-liability statute (20%): 10×. The mutual's claims barely move ($7.3m against $7.3m) because the $1bn limit binds either way; the difference lands on the labs. | **Fail** | Legislation: either strict liability with a cap (the nuclear model) or a statutory exclusion. |
| 9. The insured cannot trigger the loss | Moral hazard is controllable by the insurer | Not modelled. The mutual's conditions (evaluations, safeguards, testing periods) are the control; FRI's experts expect safeguards to cut AI-enabled bio risk by about two thirds. | **Plausible** | This is the AIUC thesis: the case for a mutual rather than a premium. |

## Sensitivity

Bio peril alone at the central rate (0.5% a year), five members with $10bn revenue each. The premium loads the 99.5% VaR, so where that VaR is zero the premium is just expected claims plus expenses.

| α | Attribution | Limit per member ($bn) | Expected claims ($bn) | Share of attributed liability paid | Premium per member, % of revenue | VaR 99.5% ($bn) | TVaR 99.5% ($bn) |
|---|---|---|---|---|---|---|---|
| 0.6 | 0.5% | 1 | 0.007 | 7.1% | 0.24% | 1.00 | 1.39 |
| 0.6 | 0.5% | 10 | 0.040 | 40.1% | 0.65% | 2.59 | 7.93 |
| 0.6 | 0.5% | 100 | 0.090 | 90.1% | 0.75% | 2.59 | 17.86 |
| 0.6 | 2.0% | 1 | 0.007 | 1.9% | 0.24% | 1.00 | 1.46 |
| 0.6 | 2.0% | 10 | 0.063 | 16.0% | 2.35% | 10.00 | 12.43 |
| 0.6 | 2.0% | 100 | 0.244 | 61.4% | 2.79% | 10.35 | 48.62 |
| 0.6 | 20.0% | 1 | 0.007 | 0.2% | 0.24% | 1.00 | 1.46 |
| 0.6 | 20.0% | 10 | 0.075 | 1.9% | 2.37% | 10.00 | 14.61 |
| 0.6 | 20.0% | 100 | 0.635 | 16.0% | 23.49% | 100.00 | 124.26 |
| 0.7 | 0.5% | 1 | 0.007 | 8.4% | 0.24% | 1.00 | 1.38 |
| 0.7 | 0.5% | 10 | 0.038 | 44.7% | 0.65% | 2.58 | 7.50 |
| 0.7 | 0.5% | 100 | 0.077 | 91.4% | 0.73% | 2.58 | 15.38 |
| 0.7 | 2.0% | 1 | 0.007 | 2.2% | 0.24% | 1.00 | 1.46 |
| 0.7 | 2.0% | 10 | 0.063 | 18.5% | 2.35% | 10.00 | 12.26 |
| 0.7 | 2.0% | 100 | 0.221 | 65.5% | 2.73% | 10.31 | 44.04 |
| 0.7 | 20.0% | 1 | 0.007 | 0.2% | 0.24% | 1.00 | 1.46 |
| 0.7 | 20.0% | 10 | 0.075 | 2.2% | 2.37% | 10.00 | 14.61 |
| 0.7 | 20.0% | 100 | 0.627 | 18.5% | 23.48% | 100.00 | 122.63 |
| 1 | 0.5% | 1 | 0.007 | 12.9% | 0.24% | 1.00 | 1.36 |
| 1 | 0.5% | 10 | 0.032 | 59.9% | 0.63% | 2.56 | 6.43 |
| 1 | 0.5% | 100 | 0.051 | 95.0% | 0.67% | 2.56 | 10.23 |
| 1 | 2.0% | 1 | 0.007 | 3.4% | 0.24% | 1.00 | 1.46 |
| 1 | 2.0% | 10 | 0.060 | 27.9% | 2.34% | 10.00 | 11.83 |
| 1 | 2.0% | 100 | 0.167 | 77.1% | 2.61% | 10.22 | 33.17 |
| 1 | 20.0% | 1 | 0.007 | 0.3% | 0.24% | 1.00 | 1.46 |
| 1 | 20.0% | 10 | 0.075 | 3.4% | 2.37% | 10.00 | 14.61 |
| 1 | 20.0% | 100 | 0.605 | 27.9% | 23.43% | 100.00 | 118.32 |
| 1.4 | 0.5% | 1 | 0.007 | 19.8% | 0.24% | 1.00 | 1.34 |
| 1.4 | 0.5% | 10 | 0.027 | 78.2% | 0.62% | 2.54 | 5.36 |
| 1.4 | 0.5% | 100 | 0.034 | 99.4% | 0.63% | 2.54 | 6.82 |
| 1.4 | 2.0% | 1 | 0.007 | 5.4% | 0.24% | 1.00 | 1.46 |
| 1.4 | 2.0% | 10 | 0.058 | 42.1% | 2.34% | 10.00 | 11.40 |
| 1.4 | 2.0% | 100 | 0.124 | 89.6% | 2.51% | 10.16 | 24.57 |
| 1.4 | 20.0% | 1 | 0.007 | 0.5% | 0.24% | 1.00 | 1.46 |
| 1.4 | 20.0% | 10 | 0.075 | 5.4% | 2.37% | 10.00 | 14.61 |
| 1.4 | 20.0% | 100 | 0.583 | 42.1% | 23.39% | 100.00 | 113.99 |
| 2 | 0.5% | 1 | 0.007 | 28.1% | 0.24% | 1.00 | 1.31 |
| 2 | 0.5% | 10 | 0.022 | 92.8% | 0.61% | 2.53 | 4.38 |
| 2 | 0.5% | 100 | 0.024 | 100.0% | 0.61% | 2.53 | 4.73 |
| 2 | 2.0% | 1 | 0.007 | 7.8% | 0.24% | 1.00 | 1.46 |
| 2 | 2.0% | 10 | 0.056 | 58.7% | 2.33% | 10.00 | 10.99 |
| 2 | 2.0% | 100 | 0.094 | 98.5% | 2.44% | 10.11 | 18.62 |
| 2 | 20.0% | 1 | 0.007 | 0.8% | 0.24% | 1.00 | 1.46 |
| 2 | 20.0% | 10 | 0.075 | 7.8% | 2.37% | 10.00 | 14.61 |
| 2 | 20.0% | 100 | 0.561 | 58.7% | 23.35% | 100.00 | 109.87 |

<!-- generated:end -->