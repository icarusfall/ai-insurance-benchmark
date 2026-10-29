# Parameter registry

Every number the catastrophe model or the site uses comes from an entry here. One file per area: `cyber.yaml`, `bio.yaml`, `market.yaml` (prices, capacity, forecasts) and `structures.yaml` (precedent schemes, regulation, the AIUC proposal).

## Entry fields

| Field | Meaning |
|---|---|
| `id` | Unique snake_case key |
| `peril` | `cyber`, `bio`, `ip`, `all`, or `structure` |
| `informs` | The model parameters it bears on, e.g. `tail_alpha`, `frequency`, `severity_anchor`, `insured_share`, `attribution`, `price_multiple`, `layer`, `capital` |
| `lens` | `scratch` (built up from first principles), `parallel` (another fat-tailed industry or past event), `market` (prices, markets, forecasting platforms), `expert` (surveys and elicitations) |
| `claim` | The finding in one or two sentences, paraphrased |
| `values` | Numbers with units; use `low`/`central`/`high` where the source gives a range |
| `source` | `title`, `author`, `publisher`, `date`, `url` |
| `accessed` | Date we read it |
| `status` | `verified`: read at the primary source or a specialist outlet quoting it. `secondary`: from news or summaries, primary not read. `unverified`: a search snippet or memory; do not use on the site until upgraded |
| `caveats` | Anything that limits the number's use |
| `mapping` | How the number becomes a model parameter (to be filled as the model takes shape) |

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
  - Live Metaculus, Manifold, Polymarket and Kalshi questions on AI incidents, AI-attributed deaths and bio events, each with its resolution criteria and liquidity.
  - Lab revenues.
  - AIUC's own product limits.
  - Munich Re aiSure.
- **Structures:**
  - P&I International Group: pool retention, general excess-of-loss reinsurance and overspill.
  - Liability Risk Retention Act and Risk Retention Group capital rules.
  - NAIC RBC factors, including the R5 catastrophe charge.
  - Solvency II standard-formula man-made liability catastrophe factors, and the rules for ancillary own funds.
  - Price-Anderson: confirm the annual payment cap after the 2023 adjustment.
- **Severity anchors:**
  - 9/11 insured loss.
  - Fukushima total cost.
  - Asbestos and opioid totals.
