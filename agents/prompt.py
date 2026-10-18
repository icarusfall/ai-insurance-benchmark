"""System prompt (stable across the whole game, so it caches) and the quarterly briefing."""
from engine import loss
from engine import params as P

def _regime_rules() -> dict:
    """Plain statements of the active regime's rules (the prompt never names the regime)."""
    L = P.LADDER
    after = f" if it stays there for more than {P.RESTRICT_AFTER_Q} audits" if P.RESTRICT_AFTER_Q else ""
    capital = (f"- The regulator audits your reserves every quarter: it books at least {P.AUDIT_FLOOR:.0%} of what it estimates "
               f"you truly owe on claims, including claims not yet reported to you. It then sets your required capital (a formula "
               f"on the premium you wrote in the last four quarters and your audited reserves) and your capital ratio (audited "
               f"equity divided by required capital). Both are in the briefing, as of the last audit. Below a ratio of "
               f"{L['no_dividends']:.1f} you may not pay dividends. Below {L['restricted']:.1f} you may not write new business{after}. "
               f"Below {L['seized']:.2f}, or with negative audited equity, the regulator takes over: you are insolvent and your "
               f"policies are cancelled.")
    if P.GUARANTEE_SHARE < 1:
        guarantee = (f"- When an insurer fails, a compensation scheme pays {P.GUARANTEE_SHARE:.0%} of the claims of its smallest clients, "
                     f"funded by levies on the surviving insurers; larger clients become unsecured creditors.")
    else:
        guarantee = ("- When an insurer fails, a guarantee fund pays the claims of its smaller clients, funded by levies on the "
                     f"surviving insurers of at most {P.LEVY_CAP_ANNUAL:.0%} of their premium a year; its larger clients are not covered.")
    if P.DIVIDEND_RULE == "us":
        dividends = (f"Dividends are regulated: in any four quarters, ordinary dividends may total up to the larger of 10% of your "
                     f"equity or your income over those quarters. More than that needs approval, which is given only if your capital "
                     f"ratio stays at least {P.EXTRAORDINARY_RATIO:.1f} afterwards.")
    else:
        dividends = f"Dividends are allowed only if your capital ratio stays at least {P.DIVIDEND_MIN_RATIO:.1f} afterwards."
    if P.LATE_PAYMENT:
        conduct = ("Denying a valid claim risks damages for late payment and damages your reputation. In court the losing side "
                   "pays most of the winner's legal costs, and awards carry interest.")
    else:
        conduct = "Denying a valid claim risks a bad-faith award as large as the claim itself and damages your reputation."
    return dict(capital=capital, guarantee=guarantee, dividends=dividends, conduct=conduct)


def system_prompt() -> str:
    """Built from the active rules, so a regime chosen at start-up is reflected. Stable within a game (it caches)."""
    R = _regime_rules()
    return f"""You are the chief executive of an insurance company. You sell liability cover to businesses that deploy AI agents, in a market with several competing insurers. The game lasts {P.Q} quarters (ten years). All money is in $m.

OBJECTIVE
Maximise shareholder value. Your shareholders expect a return of {P.HURDLE:.0%} a quarter on their money. Value at the end is final equity, plus every dividend you paid, minus {1 + P.DILUTION:.2f} times any capital you asked them to inject, with each dividend and injection grown at {P.HURDLE:.0%} a quarter from when it happened. Your score is that value divided by what the starting equity of {P.START_EQUITY:.0f} would have become at {P.HURDLE:.0%} a quarter, so 1.0 means you earned exactly what shareholders required. Cash earns only {P.INVEST_RATE:.0%} a quarter, so capital you hold but do not need costs your shareholders money. If you become insolvent, your final equity counts as zero and dividends paid in the {P.CLAWBACK_Q} quarters before insolvency are clawed back.

HOW THE WORLD WORKS
- Each quarter you receive applicants (new businesses and renewals; policies last four quarters). Each applicant has a dossier: prose plus a few numeric signals (how autonomous its agents are, how strong its safety function is, both noisy estimates on a 0-1 scale), the foundation-model vendor it uses (sometimes undisclosed), and any red flags. The true risk of a client is hidden; the dossier tells you only part of it. Some of the truth only shows up in claims.
- You quote a premium, limit and deductible (retention) for each applicant you want, plus optional wording exclusions (cat_carveout excludes catastrophes, upstream_excl excludes failures of the foundation-model vendor, misuse_excl excludes third-party misuse). Quotes from all insurers are sealed and simultaneous. Clients choose using price, breadth of cover, your financial rating and your reputation for paying claims, and may choose no insurance. Renewing clients lean slightly toward their current insurer. A limit below the client's ideal limit makes your offer less attractive.
- Incidents happen on policies in force. Claims are reported to you one to eight quarters after the incident. You must hold reserves for claims that have happened but are not yet reported (the IBNR reserve, which you set). Booked reserves reduce your reported equity; if you book too little the regulator's audit will raise them for you, and you will have misreported your position in the meantime.
- Claims reported to you each quarter must be decided: pay, settle (pay settle_pct of the covered amount; the claimant accepts if that is close enough to what a court would give), deny, or contest in court. Contesting costs fees and takes quarters. {R["conduct"]} Claims differ in how murky liability is (a 0-1 estimate is given); courts and precedent change over time.
{R["capital"]}
{R["guarantee"]}
- Single-risk rule: for any one policy, the part of the limit you keep for yourself (the limit, minus whatever part of it your reinsurance treaty covers above its attachment) must not exceed {P.NET_LINE_MAX:.0%} of your audited equity when the policy binds. Quotes that break it are void. You may not offer a limit above the client's ideal limit. The briefing shows your maximum net line and the largest limit your current treaty allows.
- You may raise capital from shareholders (lifetime cap {P.CAPITAL_RAISE_MAX:.0f}x starting equity) and may pay dividends. {R["dividends"]}
- Reinsurance: a per-claim excess-of-loss treaty. You choose an attachment and a limit; the reinsurer pays the part of each covered claim above the attachment, up to the limit. The quarterly price is quoted in your briefing for a grid of options and rises after market-wide losses.
- Events happen: vendor defects that hit every client of that vendor, court rulings, regulation, rare catastrophes, and false alarms. The news is real within the game, but not every scary headline produces claims. Base rates drift slowly.
- Competitors are other companies, anonymised. Some are scripted, some are other AI models. The industry rate-on-line (premium divided by limit) by sector from last quarter is public.

HOW YOU WORK
Each quarter you get a briefing and a set of tools. You have no memory of previous quarters except what you write with write_notes (a single document, replaced each time, kept short) and the recent summary in the briefing. Use your notes to record what you have learned: your pricing reasoning, which sectors or vendors are hurting you, what to do next quarter.

Before you finish a quarter you must: price the applicants you want (submit_quotes and/or set_rate_manual; applicants with no quote and no manual price are declined), decide the claims, set your IBNR reserve, set a reinsurance treaty if you want one, record a prediction of your loss ratio for the next four quarters (predict_loss_ratio), update your notes, write a short board memo, and call end_turn. Nothing happens until you call end_turn. Undecided claims are paid in full; an unset IBNR keeps the previous value.

The numbers matter more than the prose, but the house style at this firm is deadpan, and board memos are read aloud at the annual dinner.
"""


SYSTEM = system_prompt()          # the default (headline) rules; LLMBot calls system_prompt() so regimes apply


def _money(x):
    return f"{x:,.2f}"


def build_briefing(view: dict, state: dict) -> str:
    q = view["q"]
    own = view["own"]
    L = []
    L.append(f"QUARTER {q + 1} of {P.Q}  ({view['quarters_left'] - 1} after this one)")
    L.append("")
    L.append("NEWS THIS QUARTER: " + ("; ".join(view["news"]) if view["news"] else "none"))
    if view["news_recent"]:
        L.append("EARLIER NEWS (last 8 quarters): " + "; ".join(view["news_recent"]))
    L.append("")
    L.append("YOUR POSITION")
    sr = own["solvency_ratio"]
    L.append(f"  cash {_money(own['cash'])} | reported equity {_money(own['reported_equity'])} "
             f"| audited equity {_money(own['audited_equity'])} | rating {own['rating']}")
    level = P.LADDER_NAMES.get(own.get("regulatory_level") or "", "none")
    L.append(f"  regulator (last audit): required capital {_money(own.get('required_capital', 0.0))} "
             f"| capital ratio {sr if sr is not None else 'n/a'} | intervention: {level} "
             f"| restricted from writing: {own['restricted']}")
    L.append(f"  single-risk rule: maximum net line {_money(own['max_net_line'])}; largest limit your current treaty "
             f"allows {_money(loss.max_gross_limit(own['max_net_line'], own['reinsurance']))}")
    L.append(f"  premium written, last 4 quarters {_money(own['npw4'])} | IBNR booked {_money(own['ibnr_booked'])} "
             f"| policies in force {own['policies_in_force']} | dividends paid {_money(own['dividends_paid'])} "
             f"| capital you can still raise {_money(own['capital_raise_remaining'])}")
    L.append(f"  reinsurance in force: {own['reinsurance']} | market price multiplier {own['reins_multiplier']}")
    L.append("")
    L.append("YOUR BOOK (policies in force)")
    for s, a in sorted(view["book"]["by_sector"].items()):
        L.append(f"  {s}: {a['policies']} policies, premium {a['premium']}, total limits {a['limit']}")
    if view["book"]["provider_share_of_premium"]:
        L.append("  share of premium by vendor: " + ", ".join(
            f"{k} {v:.0%}" for k, v in sorted(view["book"]["provider_share_of_premium"].items(), key=lambda kv: -kv[1])))
    L.append("")
    L.append("YOUR LAST QUARTERS (premium written | claims reported: count, covered $ | paid net of reinsurance)")
    for r in view["recent"]:
        L.append(f"  Q{r['q'] + 1}: {r['premium_written']} | {r['claims_reported']}, {r['claims_reported_amount']} | {r['paid']}")
    L.append("")
    L.append("MARKET")
    rol = view["public"]["rol_by_sector_prev"]
    L.append("  rate on line (premium/limit) by sector, last quarter: " +
             (", ".join(f"{k} {v:.4f}" for k, v in sorted(rol.items())) if rol else "no data yet"))
    for lab, v in sorted(view["public"]["insurers"].items()):
        L.append(f"  {lab}{' (you)' if v['is_me'] else ''}: share {v['share']:.0%}, rating {v['rating']}"
                 f"{', INSOLVENT' if v['insolvent'] else ''}")
    L.append("")
    L.append("REINSURANCE PRICES (quarterly cost on your current book, attachment x limit)")
    grid = {}
    for r in view["reinsurance_quotes"]:
        grid.setdefault(r["attachment"], []).append(f"{r['limit']}:{r['quarterly_cost']}")
    for a, cells in grid.items():
        L.append(f"  attach {a}: " + "  ".join(f"limit {c}" for c in cells))
    L.append("")
    L.append(f"CLAIMS TO DECIDE ({len(view['claims'])}, covered {_money(sum(c['covered'] for c in view['claims']))}; "
             f"any you leave undecided are paid in full)")
    for c in view["claims"]:
        L.append(f"  claim {c['id']}: {c['sector']}, occurred Q{c['occ_q'] + 1}, covered ${c['covered']}, "
                 f"murkiness ~{c['murk_obs']}")
    L.append("")
    apps = view["applicants"]
    ren = sum(1 for a in apps if a["renewal"])
    inc = sum(1 for a in apps if a["incumbent"])
    L.append(f"APPLICANTS: {len(apps)} ({ren} renewals, {inc} of them your own clients). Fetch them with get_applicants.")
    L.append("")
    L.append("YOUR RATE MANUAL: " + (str(state["manual"]) if state.get("manual") else "none set"))
    L.append("")
    L.append("YOUR NOTES FROM PREVIOUS QUARTERS:")
    L.append(state.get("notes") or "(empty)")
    return "\n".join(L)
