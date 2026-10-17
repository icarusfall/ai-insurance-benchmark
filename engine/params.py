"""All tunable constants. Everything here is a [tune] placeholder until calibrated (see DESIGN.md)."""

ENV_VERSION = "0.1.0-dev"

Q = 40                      # quarters
START_EQUITY = 40.0        # $m
EXPENSE = 0.20              # of premium, paid at binding
INVEST_RATE = 0.01          # per quarter on positive cash
K_REG = 0.4                 # equity >= K_REG * trailing-4q premium written
AUDIT_FLOOR = 0.6           # regulator forces booked reserves up to this share of true unpaid
RATING_FULL = 1.5           # equity/NPW at which financial rating saturates
POLICY_TERM = 4             # quarters

SIZE_MULT = [0.5, 1.0, 2.0, 4.0, 8.0]
SIZE_WEIGHTS = [0.25, 0.30, 0.25, 0.15, 0.05]
SIZE_WORDS = ["tiny", "small", "mid-sized", "large", "enormous"]
IDEAL_LIMIT_PER_SIZE = 15.0   # $m per unit of SIZE_MULT
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
CAT_RATE = 0.03
RULING_RATE = 0.06
MANDATE_RATE = 0.02
SAFE_HARBOUR_RATE = 0.015
FALSE_ALARM_RATE = 0.06
DRIFT_SIGMA = 0.04

# arrivals
INITIAL_CLIENTS = 120
ARRIVALS_PER_Q = 10.0
ARRIVAL_GROWTH = 0.02

# claims / legal
COURT_DELAY = (2, 6)
RESERVE_CONTESTED = 0.8
SUE_PROB_AFTER_DENIAL = 0.5
BAD_FAITH_LOADING = 0.25
INTEREST_LOADING = 0.10
SETTLE_ACCEPT = 0.9         # claimant accepts settle_pct >= SETTLE_ACCEPT * p_liable
REP_START = 0.5

# guarantee fund: per-quarter levy cap as a share of an insurer's trailing-4q premium (floor 5)
LEVY_CAP = 0.12

# reinsurance (NPC reinsurer, per-claim excess of loss). Rate multiplier on expected ceded loss.
REINS_BASE_LOAD = 1.25
REINS_HARDENING = 0.8
