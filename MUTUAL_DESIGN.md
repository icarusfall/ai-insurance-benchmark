# Mutually Assured AI Modelling: design notes

A toy catastrophe model for frontier-AI liability, published as a second site from this repo, with a Substack post on which levers decide whether a frontier AI mutual is affordable or hopeless. Status: design only, nothing built (2026-10-29).

> This is a toy model to take the idea out for a walk, not to definitively price catastrophe.

The name is a nod to MAIM, "Mutual Assured AI Malfunction" (Hendrycks, Schmidt and Wang, *Superintelligence Strategy*). The site should say so in one line, so readers who don't know the reference aren't lost.

## 1. What we are responding to

Trout, Kvist and Dattani (AIUC), *Bootstrapping Frontier AI Governance by Mutualizing Risk*, Lawfare, 22 September 2026. The AIUC post of 23 September summarises it. Their proposal:

- **The mutual.** It would be owned by the frontier labs it covers. Members put capital into a fund that pays when any member causes harm, and the excess is returned if incidents are few.
- **Governance.** A CEO with a duty to the membership as a whole. Insurance-regulator oversight. Membership conditioned on minimum safety standards.
- **Three products, in order of importance:**
  1. Third-party liability, including mass casualties, CBRN and critical infrastructure. These perils are almost universally excluded by commercial insurers.
  2. First-party AI cyber cover.
  3. Business interruption when a dangerous capability forces a rollback.
- **Enforcement levers.**
  - Notice of incidents within 24–72 hours.
  - Mutual-chosen incident response.
  - Audits and evaluations contracted by the mutual.
  - Minimum testing periods.
  - Premium increases.
  - Suspension or expulsion.
  - The McCarran-Ferguson antitrust carve-out lets members share data and standards.
- **Size.** "Capital (billions, we expect)". About $1bn of cover per member as the minimum that justifies serious technical underwriting.
- **Track record of insurers.** 1970s nuclear insurers estimated core melts at about 1 in 400 reactor-years, within an order of magnitude of what turned out to be true. The government estimate of the time was 1 in 20,000.
- **Insurability.** Insurers can hold billions of exposure to events whose damage runs to trillions; life insurers weathered COVID. Uninsurable risks such as extinction can still be modelled and mitigated, just not priced.
- **Premiums matter mainly for their information value.** The governance comes from audits and standards.

**What they leave open, and where this project adds something:**

- No parameterisation.
- No capital adequacy test.
- No view on paid-in versus callable capital.
- No view on correlation between members.
- No reinsurance, capital-market or government layer.

Their claim that a $1bn slice of a trillion-dollar risk is insurable is a quantitative claim, and we can test it.

## 2. Questions the site and post should answer

1. Given a risk profile, what is a sensible premium for $X of cover per member? Is that premium a rounding error or a large share of a lab's revenue?
2. How much capital does that cover need?
   - In US terms: statutory reserves, RBC, and a rating-agency VaR.
   - In Solvency II terms: SCR, MCR, technical provisions and risk margin.
3. Which few levers move the answer from "affordable" to "absurd"?
4. **Bio:** prove or disprove that it is uninsurable, and say precisely what "uninsurable" means.
5. **Catastrophe bonds:** what would a cat bond on AI risk look like? Expected loss, chance of attaching, indicative spread, trigger design, and whether investors would be right to call it uncorrelated.

## 3. Architecture

A monorepo. The catastrophe model is a package of its own, imported by both sites.

```
catmodel/            plain Python, no LLM dependencies
  dist.py            truncated Pareto severity above an event threshold; closed-form layer expectations; sampling
  model.py           perils, settings, loading defaults.yaml; Monte Carlo of years (gamma-mixed rates, common-mode
                     events, per-event limits and annual aggregates per member)
  defaults.yaml      starter-for-ten parameters with optimistic/central/pessimistic values, basis and source ids
  pricing.py         the layer stack (reinsurance or cat bond, government share, premium, paid-in capital, calls),
                     premium, cat bond pricing (multiple of EL, Lane, Wang transform)
  reserves.py        year-end reserves from payment lags: undiscounted (US) and best estimate (Solvency II)
  capital_us.py      RBC-style ratio and action levels, rating-agency 99.6% test
  capital_s2.py      SCR (99.5% 1-year VaR), MCR, risk margin, own funds tiers including ancillary member calls
  report.py          `python -m catmodel.report [--level pessimistic] [--set name=value] [--bond 2,4]`
  sources/           parameter registry, YAML: every number with its range and provenance
tests/test_catmodel.py, tests/test_sources.py
mutual_site/         second static site: own Railway service, root dir mutual_site, Caddy like website/
  public/            pages, JS port of the model, data.js built from catmodel and sources/
  build.py           exports scenarios, registry and golden results for parity tests
engine/ agents/ website/ ...   the benchmark, unchanged
```

- **The benchmark stays at v0.3.** Later, the benchmark's catastrophe process switches to `catmodel` under a new ENV_VERSION (v0.4), so waves 4 and 5 stay comparable among themselves.
- **The browser needs live sliders.**
  - Python is the reference and is tested.
  - A small JavaScript port runs in the page.
  - A parity test checks both against golden results on fixed parameter sets.
  - Closed-form Pareto layer formulas keep most outputs analytic. Monte Carlo is only needed for correlation and aggregate effects (about 100k years runs comfortably in JS).
  - Pyodide is the fallback if the port drifts. It costs a heavy first load.
- **Style.** The same light pastel style family as the benchmark site, but its own identity.

## 4. The model

### Perils

Each peril has:

- **Annual frequency.** A rate with a trend, and uncertainty in the rate itself (a gamma-mixed Poisson), because we don't know the rate.
- **Ground-up severity.** The total harm in the world: a lognormal body with a Pareto tail above a threshold. The **tail index α** is the headline parameter.
- **Attribution share.** The fraction of harm a court puts on a lab. This covers causation, superseding criminal acts, and comparative fault.
- **Insurable share.** What's left after fines and penalties, punitive damages where uninsurable, war and terrorism exclusions, and intentional acts.
- **Member correlation.** The chance one event triggers claims against several labs: shared techniques, shared jailbreaks, open weights.
- **Reporting and payment pattern.** Months for an outage, decades for a mass tort. This drives reserves and discounting.

Starting list:

| Peril | Main parallels | Expected character |
|---|---|---|
| AI-enabled cyberattack on infrastructure or software supply chain | NotPetya, WannaCry, CrowdStrike 2024, Lloyd's systemic cyber scenarios | Fat-tailed, correlated across victims and possibly members |
| Bio / CBRN uplift | 2001 anthrax letters, Aum Shinrikyo; COVID as the upper bound | Extreme tail, low attribution, the case to prove uninsurable (section 5) |
| Agentic financial harm | Knight Capital 2012, 2010 flash crash | Fast, bounded per event, correlated |
| Mass tort (self-harm, product defect) | Opioids, tobacco, asbestos, Roundup | Long latency, social inflation, reserve deterioration |
| IP and privacy class actions | Bartz v. Anthropic settlement | Frequent and large, attritional rather than catastrophic |
| First-party AI cyber and business interruption (the essay's products 2 and 3) | Standard cyber cover | Higher frequency, gives the mutual loss feedback |
| Loss of control | – | Out of scope: no claimant or payer would be left. Model and mitigate, never price, as the essay says |

### Structure and outputs

**Layer stack** (each layer optional):

1. Member retention.
2. The mutual's layer: per-event and annual aggregate limits, per member and pooled.
3. Callable capital: retrospective assessments, as in Price-Anderson's second layer and P&I overspill calls.
4. Reinsurance or cat bond.
5. A government backstop above a threshold, as in TRIA.
6. Anything above that falls back on victims and the labs.

**Outputs:**

- An exceedance-probability curve, for one year and for each layer.
- Expected loss per layer.
- Premium: expected loss + expenses + cost of capital.
- Premium as a share of member revenue.
- Capital in US terms and in Solvency II terms.
- The share of expected harm actually covered.
- Cat bond metrics.

## 5. Bio: proving it out rather than asserting it

"Uninsurable" will be broken into tests the model can pass or fail, and shown per peril on the site. Berliner's insurability criteria (1982) are a good spine:

1. **Finite mean.** If the ground-up tail index α ≤ 1, the expected loss of an unlimited policy is infinite, so no premium exists. Bio severity estimates (casualties, economic loss) may well sit near or below 1. Which estimates support which α?
2. **Capped slice.** Every capped layer has a finite mean and a finite capital need. So the precise claim becomes: "the risk is uninsurable; a $1bn slice is insurable, but it covers only a tiny share of the expected harm". The site can show that share directly. This is the essay's argument, quantified.
3. **Attribution.** Deliberate criminal misuse is a classic superseding cause in tort. The share of bio harm that could be pinned on a lab may be small, which makes the insured slice cheap but nearly irrelevant. Statute could change that (strict liability), and the model should show both regimes.
4. **Capital.** At a 99.5% or 1-in-1000 standard, does a meaningful bio limit need more capital than the members could plausibly commit? Express it as a multiple of revenue or of annual safety spending.
5. **Wrong-way risk.** A pandemic-scale event would hit the mutual's own assets (equity and credit markets), member solvency (so callable capital is unpaid exactly when needed), and investors in any cat bond at the same moment. Insurance relies on diversification, and this destroys it. A real-world parallel: the World Bank pandemic catastrophe bonds were criticised for paying too little, too late.
6. **Public policy and moral hazard.** Some of this is unpriceable for legal reasons (terrorism and war exclusions), and some because the insured influences the trigger.

The result for bio is a table: which criteria fail, at what parameter values, and what it would take for each to pass. Possible answers: a cap, a government layer, strict liability, or diversified investors.

## 6. Catastrophe bonds on AI risk (a side track)

Same underlying distribution, different wrapper. For each candidate bond:

- **Trigger design.**
  - **Indemnity:** the mutual's actual losses. Least basis risk, but moral hazard, because the sponsor can influence how losses are settled.
  - **Industry index:** total insured AI losses, if such an index ever exists.
  - **Parametric:** a declared incident class or an outage of more than N hours. CrowdStrike-style parametric cyber covers already exist.
  - **Modelled loss.**
- **Metrics:**
  - Attachment probability and exhaustion probability.
  - Expected loss.
  - Indicative spread from (a) a multiple of expected loss, taken from cyber and nat-cat bond history, (b) the Lane (2000) pricing model, and (c) a Wang transform with a parameter fitted to market spreads.
- **Pricing for model uncertainty.** Novel perils trade at higher multiples of expected loss, so the toy can show spread against the size of disagreement between sources.
- **The correlation question.** Cat bonds sell as near zero-beta, uncorrelated with markets. AI companies now make up a large share of equity market value, so an AI catastrophe is plausibly correlated with the investor's other holdings. That is a substantive point for a finance audience: it may matter more than the expected loss itself.
- **Parallels to check:**
  - The first cyber cat bonds (2023 onwards).
  - Terrorism and pandemic bonds: World Bank PEF, Golden Goal Finance for the 2006 World Cup.
  - Longevity and mortality bonds, the other "humanity-scale" underlying.

## 7. Parameter sources: a registry with three viewpoints

Each parameter in `catmodel/sources/*.yaml` records:

- the low, central and high values;
- the viewpoint it comes from (first principles, parallel industry, or market or expert);
- the source, its URL, the date it was accessed, and a confidence rating;
- a note on how the source's numbers were turned into ours.

The site shows a triangulation chart for each parameter, and lets the reader choose which viewpoints feed the central case. Nothing goes on the site without a dated, linked source.

**A. From first principles**

- **Fault trees per peril:** P(attempt) × P(the model gives meaningful uplift despite safeguards) × P(success) × harm. Inputs:
  - lab system cards and capability thresholds (Anthropic's ASL levels, OpenAI's Preparedness Framework);
  - uplift studies (RAND red-team work and later ones).
- **Attack base rates:** the Global Terrorism Database, and Clauset et al. on power-law tails in terrorism severity.
- **AI and cyber incident counts and severities:**
  - the AI Incident Database, OECD's AI Incidents Monitor and the MIT AI Risk Repository;
  - VERIS and Cyentia data;
  - academic cyber-loss studies such as Eling's.

**B. Parallels from other fat-tailed industries**

- **Nuclear.**
  - Price-Anderson: a primary layer of insurance plus a retrospective assessment pooled across reactors, which amounts to callable capital.
  - The nuclear mutuals (NEIL, ELINI), and INPO tied to the mutual's premiums, which the essay itself cites.
  - Fukushima and Chernobyl as severity anchors.
- **Terrorism.** TRIA, Pool Re and GAREAT (government backstops above an industry retention); 9/11 as the insured-loss anchor.
- **P&I clubs.** The International Group's pooling, excess-of-loss reinsurance and overspill calls.
- **Risk Retention Groups** (US Liability Risk Retention Act 1986). The probable US legal vehicle for a liability mutual of similar businesses.
- **Vaccines** (NVICP, PREP Act). A no-fault fund plus liability immunity, as the alternative design.
- **Medical malpractice mutuals.** The essay's own example of risk reduction, with loss histories before and after.
- **Mass torts.** Asbestos, opioids, tobacco, Roundup: latency, social inflation, and reserves strengthened again and again.
- **Cyber catastrophe.** Lloyd's and Cambridge systemic scenarios, CyberCube, Moody's RMS, and the war-exclusion litigation after NotPetya.

**C. Markets and forecasters**

- **Forecasting.**
  - Metaculus and Manifold (long-dated questions); Polymarket and Kalshi (liquid but short-dated).
  - Questions on AI-driven cyberattacks, AI-attributed deaths, bio events and lawsuits against labs.
  - Record each question's resolution criteria and liquidity alongside its probability.
- **Expert elicitation.** The Forecasting Research Institute's tournament (XPT), where superforecasters and experts disagreed by an order of magnitude, and the AI Impacts surveys. The spread between them is itself an input.
- **Price of risk.** Cat bond spreads against expected loss (Artemis data), and cyber cat bond pricing specifically.
- **Current AI insurance market.** Limits and prices from AIUC, Armilla, Munich Re (aiSure) and Lloyd's coverholders.
- **Ability to pay.** Lab revenues, funding and valuations.
- **Legal regime.**
  - The revised EU Product Liability Directive, which now covers software.
  - The withdrawn EU AI Liability Directive.
  - California SB 53, New York's RAISE Act, and current suits against labs.
  - Together these feed attribution and insurable share.

## 8. Capital in two languages

| | US | Solvency II |
|---|---|---|
| Liabilities | Statutory case reserves, IBNR, LAE, unearned premium; Schedule P-style development triangles | Best estimate (discounted) + risk margin at a cost of capital (6%, reduced to 4.75% by the 2025 review: verify) |
| Required capital | NAIC RBC with action levels at 200/150/100/70% of authorised control level (as in the benchmark's v0.3 ladder); rating-agency view such as AM Best's capital model at 99.6% VaR | SCR = 1-year 99.5% VaR (standard formula: premium and reserve risk, man-made liability catastrophe; or an internal model, more realistic for a new peril); MCR |
| Callable capital | Assessable mutual policies; RRG assessments | Supplementary member calls count as Tier 2 ancillary own funds, with supervisory approval |
| Vehicle | Risk Retention Group (Vermont, say) or a captive | EU or UK mutual; Bermuda (BSCR) as a later variant, matching the benchmark's planned Bermuda preset |

## 9. Likely headline levers

1. **Tail index α.** Below 2 the variance is infinite; at or below 1 even the mean is infinite, and only capped layers can be priced.
2. **Layer design.** Per-event and aggregate limits, and the attachment of any government backstop. Capital scales with the limit, not with the tail.
3. **Callable capital versus paid-in capital.** Retrospective assessments turn an unaffordable fund into a contingent commitment, but they are only worth as much as members' solvency in the same bad year.
4. **Correlation across members.** A jailbreak that works on every lab's model removes the diversification.
5. **Attribution and insurable share.** Where the law lands.
6. **The safety standard and the cost of capital.** 99.5% against 1-in-1000; 4.75% against 10%+.
7. **Reporting lag.** Latency of years means larger reserves and more uncertainty.
8. **Risk reduction.** The mutual's audits and standards, as a multiplier on frequency. This is the AIUC thesis, and the model can show how much risk reduction the mutual has to deliver to pay for itself.
9. **Disagreement between sources.** How much of the premium is a load for not knowing the distribution, priced either through capital or through a cat bond spread.

## 10. Phases

0. **Sourcing pass.** Fill the registry for the perils above, each figure dated and linked. Bio and cyber first.
1. **`catmodel` in Python.** Distributions with closed-form checks, layers, Monte Carlo, US and Solvency II capital, cat bond pricing, tests.
2. **The site.** Lever board, exceedance-probability curves, triangulation charts, the bio insurability table, a cat bond explorer, and "this is a toy" said early and often. Deployed on Railway.
3. **Substack post.** Built around the levers in section 9, with links into the site at the exact settings discussed.
4. **Benchmark v0.4.** The benchmark's catastrophe process draws on `catmodel` perils.

## Open questions

- Members: model the named frontier labs explicitly (revenues are public) or as anonymous archetypes? Archetypes avoid implying anything about real companies, and the site could still show "a lab with revenue $X".
- Main currency: US dollars throughout, with Solvency II figures also in dollars?
- How far to take reserving: development triangles and IBNR, or a simpler payment pattern with discounting?
