"""All tunable constants. Everything here is a [tune] placeholder until calibrated (see DESIGN.md)."""

BASE_VERSION = "0.4.0-dev"   # 0.4: catastrophes from catmodel perils (fat tails, vendor concentration, attribution,
                             #      capability growth). 0.3: graded capital ladder, dividend rule, levy cap, regimes
ENV_VERSION = BASE_VERSION   # gains a "+uk" suffix under set_regime("uk")

Q = 40                      # quarters
START_EQUITY = 40.0        # $m
EXPENSE = 0.20              # of premium, paid at binding
INVEST_RATE = 0.01          # per quarter on positive cash
K_REG = 0.4                 # used only by the scripted actuary's capacity rule since v0.3 (the regulator uses LADDER)
AUDIT_FLOOR = 0.6           # regulator forces booked reserves up to this share of true unpaid
RATING_FULL = 1.5           # equity/NPW at which financial rating saturates
POLICY_TERM = 4             # quarters

SIZE_MULT = [0.5, 1.0, 2.0, 4.0, 8.0]
SIZE_WEIGHTS = [0.25, 0.30, 0.25, 0.15, 0.05]
SIZE_WORDS = ["tiny", "small", "mid-sized", "large", "enormous"]
IDEAL_LIMIT_PER_SIZE = 6.0    # $m per unit of SIZE_MULT (v0.1: 15)
MAX_LIMIT_MULT = 1.0          # quotes above this multiple of the ideal limit are void (v0.1: 1.5)
CAT_SCALE_PER_SIZE = 15.0     # catastrophe gross loss scale, $m per unit of SIZE_MULT (kept at v0.1 size)
RETENTION_PER_SIZE = 0.02

# frequency (incidents/yr at size 1), severity median ($m), lognormal sigma, base liability, sector weight
SECTORS = {
    "medical":          dict(freq=0.30, median=0.35, sigma=1.2, weight=0.14),
    "finance":          dict(freq=0.35, median=0.30, sigma=1.2, weight=0.16),
    "logistics":        dict(freq=0.30, median=0.20, sigma=1.1, weight=0.14),
    "customer_service": dict(freq=0.60, median=0.08, sigma=1.0, weight=0.20),
    "legal_hr":         dict(freq=0.30, median=0.25, sigma=1.1, weight=0.10),
    "infrastructure":   dict(freq=0.12, median=1.00, sigma=1.3, weight=0.06),
    "defence":          dict(freq=0.10, median=1.20, sigma=1.3, weight=0.04),
    "consumer":         dict(freq=0.50, median=0.10, sigma=1.0, weight=0.16),
}
SECTOR_NAMES = list(SECTORS)
SECTOR_IDX = {n: i for i, n in enumerate(SECTOR_NAMES)}

TAIL_P = 0.03               # probability an incident is a tail event
TAIL_XM = 4.0               # Pareto scale multiplier
TAIL_ALPHA = 2.2

# risk-factor coefficients (truth)
B_AUTONOMY = 1.0
B_SAFETY = -1.2
B_CORNER = 0.35
MISUSE_SHARE = 0.15         # share of incidents that are third-party misuse

PROVIDER_NAMES = ["Gorbly", "Yottabrain", "Mindful Systems", "ChadGPT",
                  "Cogitron Heavy Industries", "Colossal Dynamics"]
PROVIDER_SHARES = [0.30, 0.22, 0.18, 0.12, 0.10, 0.08]

# event rates per quarter (events only after quarter 3)
RULING_RATE = 0.06
MANDATE_RATE = 0.02
SAFE_HARBOUR_RATE = 0.015
FALSE_ALARM_RATE = 0.06
DRIFT_SIGMA = 0.04

# --------------------------------------------------------------------------- catastrophes (v0.4, from catmodel/)
# Each peril follows catmodel/defaults.yaml in shape: a gamma-mixed Poisson rate (redrawn each game year), a truncated
# Pareto event size S (1 to cap, tail index alpha), a chance the event is "common mode" (every vendor's models to blame)
# and otherwise one vendor's, a legal attribution factor on liability, and rates that rise with AI capability as
# min(cap_mult, (horizon / horizon at the start) ** elasticity). Rates are per quarter at the start of the game.
# A client's chance of being hit by an event is min(HIT_MAX, hit * sqrt(S)) times its vendor's concentration factor,
# and each hit's gross loss is the v0.3 per-client catastrophe loss times sqrt(S), so an event's total loss scales
# with S. The rates, hits and caps are set for the game (calibrated with the bots); tail indices, rate uncertainty,
# common mode and elasticities are catmodel's central values except where noted.
PERILS = {
    "cyber_misuse": dict(label="AI-enabled cyber attack by a third party", rate=0.02, alpha=1.1, cap=30.0, hit=0.0035,
                         rate_cv=0.5, common_mode=0.2, attribution=0.6, misuse=True, insured=True,
                         elasticity=0.3, cap_mult=3.0),      # catmodel cap_mult 5; attribution: superseding cause
    "agent_runaway": dict(label="the client's own agents ran away", rate=0.03, alpha=1.0, cap=20.0, hit=0.0016,
                          rate_cv=0.5, common_mode=0.0, attribution=1.0, misuse=False, insured=True,
                          elasticity=0.5, cap_mult=4.0),     # catmodel elasticity 1.0, cap_mult 50: unplayable in a game
    "bio_misuse": dict(label="AI-assisted engineered epidemic", rate=0.00125, alpha=0.7, cap=100.0, hit=0.0,
                       rate_cv=1.0, common_mode=0.1, attribution=0.0, misuse=True, insured=False,
                       elasticity=0.15, cap_mult=1.5),       # news only: catmodel finds it uninsurable; wordings exclude it
}
HIT_MAX = 0.25
CONC_IN = 4.0               # a one-vendor event: that vendor's clients are hit this many times more often than average;
                            # other clients less, so that across the market the average is unchanged

# AI capability: METR-style 50% time horizon in hours. Each seed draws one path (catmodel/trajectory.py).
HORIZON_START = 50.0
CAPABILITY_PATHS = {"plateau": 1 / 3, "metr_long_run": 1 / 3, "metr_2023": 1 / 3}
DOUBLING_Q = {"metr_2023": 128.7 / 91.3, "metr_long_run": 187.8 / 91.3}   # quarters per doubling
PLATEAU_CEILING = 167.0     # hours; the plateau starts at the metr_2023 slope and flattens towards this

# arrivals
INITIAL_CLIENTS = 120
ARRIVALS_PER_Q = 10.0
ARRIVAL_GROWTH = 0.02

# claims / legal
COURT_DELAY = (2, 6)
RESERVE_CONTESTED = 0.8
SUE_PROB_AFTER_DENIAL = 0.8   # v0.1: 0.6
BAD_FAITH_LOADING = 1.0       # v0.1: 0.5
INTEREST_LOADING = 0.10
CONTEST_FEE = 0.10            # of covered, when contesting (v0.1: 0.03)
REJECTED_SETTLE_FEE = 0.05    # of covered, when a settlement offer is refused and goes to court (v0.1: 0.02)
SETTLE_ACCEPT = 0.9         # claimant accepts settle_pct >= SETTLE_ACCEPT * p_liable
REP_START = 0.5

# guarantee fund (v0.3: annual cap, as US guaranty associations; v0.2 had 12% a quarter)
LEVY_CAP_ANNUAL = 0.02     # guarantee levies per insurer: at most 2% of trailing-4q premium (floor 5) in any 4 quarters

# reinsurance (NPC reinsurer, per-claim excess of loss). Rate multiplier on expected ceded loss.
REINS_BASE_LOAD = 1.25
REINS_HARDENING = 0.8
REINS_NOISE = 0.15            # lognormal sigma on the reinsurer's view of expected loss (own RNG stream)

# single-risk rule: net retained limit per policy <= this share of audited equity at binding
NET_LINE_MAX = 0.25

# capital raising: shareholders inject cash; each $ injected costs (1 + DILUTION) in the score
CAPITAL_RAISE_MAX = 1.0      # lifetime cap as a multiple of START_EQUITY
DILUTION = 0.25

# scoring: shareholders' required return. Dividends and injections compound at this rate to the end;
# the headline ratio R = value / (START_EQUITY * (1 + HURDLE) ** Q), so R = 1 means the hurdle was earned.
HURDLE = 0.02                # per quarter
CLAWBACK_Q = 8               # dividends paid within this many quarters before insolvency are clawed back
LOG_FLOOR_R = 0.1            # floor for the secondary log score ln(R)


# --------------------------------------------------------------------------- regulatory regime (v0.3)
# The headline environment is US-flavoured. Required capital is a simplified risk-based formula on trailing
# premium P and audited reserves R:  REQ_SCALE * sqrt((a P)^2 + (b R)^2 + 2 c (a P)(b R)), at least REQ_MIN.
# The capital ratio is audited equity / required capital, and the regulator acts on a graded ladder.
REGIME = "us"
REQ_PREMIUM_FACTOR = 0.22
REQ_RESERVE_FACTOR = 0.30
REQ_CORR = 0.0
REQ_SCALE = 1.0
REQ_MIN = 1.0
# ladder (capital ratio below the level -> consequence). US RBC action levels: company 200%, regulatory 150%,
# mandatory control 70%.
LADDER = {"no_dividends": 2.0, "restricted": 1.5, "seized": 0.7}
LADDER_NAMES = {"no_dividends": "company action level: no dividends, file a capital plan",
                "restricted": "regulatory action level: no new business",
                "seized": "mandatory control level: the regulator takes over"}
RESTRICT_AFTER_Q = 0        # quarters below the restriction level before it bites (UK: a recovery period)
DIVIDEND_RULE = "us"        # us: ordinary dividends up to max(10% of equity, last 4 quarters' income) in any 4
EXTRAORDINARY_RATIO = 3.0   #     quarters; more ("extraordinary") only if the ratio stays at least this high after
DIVIDEND_MIN_RATIO = 2.0    # no dividend may take the capital ratio below this
GUARANTEE_MAX_SIZE = 2      # largest client size band the guarantee scheme protects (US: large insureds excluded)
GUARANTEE_SHARE = 1.0       # share of a protected claim the scheme pays
CLAIMANT_COSTS = 0.0        # losing in court: also pay the claimant's costs, as a share of the claim (UK: loser pays)
COST_RECOVERY = 0.0         # winning in court: recover this share of your own legal fee (UK: loser pays)
SEVERITY_MULT = 1.0         # size of awards relative to the US (UK: no civil juries, lower awards)
RULING_SCALE = 1.0          # size of precedent shifts (UK: one main jurisdiction)
LATE_PAYMENT = False        # UK: no bad-faith tort; wrongful denial costs late-payment damages instead

REGIMES = {
    "us": {},
    # Hidden extra: a UK (Solvency UK, which for this game is Solvency II) flavoured variant.
    "uk": dict(REQ_PREMIUM_FACTOR=0.14 * 3, REQ_RESERVE_FACTOR=0.11 * 3, REQ_CORR=0.5,    # standard-formula style SCR
               LADDER={"no_dividends": 1.3, "restricted": 1.0, "seized": 0.35},         # SCR 100%, MCR ~35% of SCR
               LADDER_NAMES={"no_dividends": "below the firm's capital buffer: no dividends",
                             "restricted": "SCR breached: recovery plan, then no new business after two quarters",
                             "seized": "MCR breached: authorisation withdrawn"},
               RESTRICT_AFTER_Q=2, DIVIDEND_RULE="uk", DIVIDEND_MIN_RATIO=1.3,
               GUARANTEE_MAX_SIZE=0, GUARANTEE_SHARE=0.9,                  # FSCS: small businesses only, 90%
               BAD_FAITH_LOADING=0.15, LATE_PAYMENT=True,                  # late-payment damages, not bad faith
               INTEREST_LOADING=0.08, CLAIMANT_COSTS=0.15, COST_RECOVERY=0.6,
               SEVERITY_MULT=0.8, RULING_SCALE=0.7),
}


def set_regime(name: str) -> None:
    """Switch every rule to a regime preset. Call once, before building any World or Market."""
    if name not in REGIMES:
        raise ValueError(f"unknown regime {name}; choose from {list(REGIMES)}")
    g = globals()
    g.update(_US_DEFAULTS)
    g.update(REGIMES[name])
    g["REGIME"] = name
    g["ENV_VERSION"] = BASE_VERSION + ("" if name == "us" else "+" + name)
    from . import loss                      # severity caches depend on SEVERITY_MULT
    loss.layer_expectation.cache_clear()
    loss.cat_layer_expectation.cache_clear()
    from . import perils
    perils.event_layer_expectation.cache_clear()


_US_DEFAULTS = {k: globals()[k] for k in set().union(*REGIMES.values())}
