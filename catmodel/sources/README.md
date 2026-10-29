# Parameter registry

Every number the catastrophe model or the site uses comes from an entry here. `market_snapshot.yaml` is not registry entries but the prediction-market prices behind the Markets preset (`python -m catmodel.markets`). One file per area: `capability.yaml` (how fast AI improves), `cyber.yaml`, `bio.yaml`, `market.yaml` (prices, capacity, forecasts) and `structures.yaml` (precedent schemes, regulation, the AIUC proposal).

## Entry fields

| Field | Meaning |
|---|---|
| `id` | Unique snake_case key |
| `peril` | `cyber`, `bio`, `ip`, `all`, or `structure` |
| `informs` | The model parameters it bears on, e.g. `tail_alpha`, `frequency`, `severity_anchor`, `insured_share`, `attribution`, `price_multiple`, `layer`, `capital`, `trajectory` |
| `lens` | `scratch` (built up from first principles), `parallel` (another fat-tailed industry or past event), `market` (prices, markets, forecasting platforms), `expert` (surveys and elicitations) |
| `claim` | The finding in one or two sentences, paraphrased |
| `values` | Numbers with units; use `low`/`central`/`high` where the source gives a range |
| `source` | `title`, `author`, `publisher`, `date`, `url` |
| `accessed` | Date we read it |
| `status` | `verified`: read at the primary source or a specialist outlet quoting it. `secondary`: from news or summaries, primary not read. `unverified`: a search snippet or memory; do not use on the site until upgraded |
| `caveats` | Anything that limits the number's use |
| `mapping` | How the number becomes a model parameter (to be filled as the model takes shape) |
| `checks` | For a constant hard-coded in the model: `constant`, the `model` value, the `source` value and the `result` (`confirmed`, `corrected` or `re-fitted`). The site lists these. |

Rules: paraphrase, never paste; one short quote at most per entry; a figure only goes on the site at `verified` or `secondary` status, labelled as such.

## Still to source

- **Cyber:**
  - Eling & Wirfs (2019): their fitted tail parameter.
  - Eling, Ibragimov & Ning, on Hill estimates below 1: read in full.
  - AI Incident Database and OECD AI Incidents Monitor: counts and growth.
  - Knight Capital (2012) and the 2010 flash crash, for agentic financial harm.
- **Bio:**
  - The legal treatment of deliberate criminal misuse as a superseding cause, and how strict liability would change it.
  - PREP Act and NVICP mechanics.
  - World Bank pandemic bonds (PEF): terms and payout history.
  - Anthropic ASL-3 and OpenAI "High" bio capability: dates and definitions.
  - The 2023 correction to Marani et al.: which return periods stand.
- **Market:**
  - Prediction markets on AI-enabled bio events (none found with an AI-specific definition), and deeper real-money markets on AI incidents.
  - Disclosed frontier-model revenue for Google, Meta and xAI (the defaults assume about $5bn each).
  - AIUC's own product limits.
  - Munich Re aiSure.
- **Structures:**
  - P&I International Group: pool retention, general excess-of-loss reinsurance and overspill.
  - Liability Risk Retention Act and Risk Retention Group capital rules.
  - NAIC RBC factors, including the R5 catastrophe charge.
  - Solvency II standard-formula man-made liability catastrophe factors.
  - The Solvency II text as amended by the 2025 review: whether the Annex II and XIX rows changed.
  - Price-Anderson: confirm the annual payment cap after the 2023 adjustment.
- **Capability:**
  - Evidence for how each peril's rate scales with the time horizon. The elasticities and caps in `defaults.yaml` are judgement.
  - METR measurements beyond Mythos Preview, once its suite reaches past 16 hours.
- **Severity anchors:**
  - 9/11 insured loss.
  - Fukushima total cost.
  - Asbestos and opioid totals.
