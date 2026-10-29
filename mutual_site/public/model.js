// The toy catastrophe model, ported from catmodel/ (Python is the reference). Money in $bn, rates per year.
// Closed forms match Python exactly; the simulation uses its own random numbers, so simulated results match
// Python statistically, not digit for digit. tests/test_mutual_site.py checks both.
(function (root) {
  "use strict";

  // ---- severity: truncated Pareto above an event threshold (catmodel/dist.py)
  function TP(xm, alpha, cap) {
    if (!(xm > 0 && xm < cap) || !(alpha > 0)) throw new Error("bad severity");
    const c = Math.pow(xm / cap, alpha);
    const intPower = (a, b) => {                 // integral of (xm/x)^alpha over [a, b]
      if (b <= a) return 0;
      if (Math.abs(alpha - 1) < 1e-12) return xm * Math.log(b / a);
      const k = 1 - alpha;
      return Math.pow(xm, alpha) * (Math.pow(b, k) - Math.pow(a, k)) / k;
    };
    const sf = x => x < xm ? 1 : x >= cap ? 0 : (Math.pow(xm / x, alpha) - c) / (1 - c);
    const layer = (retention, limit) => {
      const lo = Math.max(retention, 0), hi = lo + Math.max(limit, 0);
      const flat = Math.max(Math.min(hi, xm) - lo, 0);
      const a = Math.max(lo, xm), b = Math.min(hi, cap);
      const tail = b > a ? (intPower(a, b) - c * (b - a)) / (1 - c) : 0;
      return flat + tail;
    };
    const quantile = p => xm * Math.pow(c + (1 - p) * (1 - c), -1 / alpha);
    return { xm, alpha, cap, sf, layer, quantile, mean: () => layer(0, cap) };
  }

  // ---- random numbers: mulberry32, Box-Muller, Marsaglia-Tsang gamma, Knuth Poisson
  function rng(seed) {
    let a = seed >>> 0;
    const u = () => {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const normal = () => Math.sqrt(-2 * Math.log(1 - u())) * Math.cos(2 * Math.PI * u());
    const gamma = (k, scale) => {
      if (k < 1) return gamma(k + 1, scale) * Math.pow(u(), 1 / k);
      const d = k - 1 / 3, c = 1 / Math.sqrt(9 * d);
      for (;;) {
        let x, v;
        do { x = normal(); v = 1 + c * x; } while (v <= 0);
        v = v * v * v;
        const w = u();
        if (w < 1 - 0.0331 * x * x * x * x || Math.log(w) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v * scale;
      }
    };
    const poisson = lam => {
      if (lam <= 0) return 0;
      if (lam > 30) return Math.max(0, Math.round(lam + Math.sqrt(lam) * normal()));
      const L = Math.exp(-lam);
      let k = 0, p = 1;
      do { k++; p *= u(); } while (p > L);
      return k - 1;
    };
    return { u, normal, gamma, poisson };
  }

  // ---- normal distribution helpers for the Wang transform
  function erf(x) {                              // Abramowitz-Stegun 7.1.26, |error| < 1.5e-7
    const s = Math.sign(x); x = Math.abs(x);
    const t = 1 / (1 + 0.3275911 * x);
    const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
    return s * y;
  }
  const ncdf = x => 0.5 * (1 + erf(x / Math.SQRT2));
  function ninv(p) {                             // Acklam's rational approximation
    const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
    const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
    const lo = 0.02425, hi = 1 - lo;
    let q, r;
    if (p < lo) { q = Math.sqrt(-2 * Math.log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1); }
    if (p > hi) { q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1); }
    q = p - 0.5; r = q * q;
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
  }

  // ---- settings from the exported defaults (catmodel/model.py load)
  const LEVELS = ["optimistic", "central", "pessimistic"];
  function pick(spec, level) {
    if (spec === null || typeof spec !== "object") return spec;
    if (level === "central") return spec.central;
    const bad = spec.worse || "high";
    const end = level === "pessimistic" ? bad : (bad === "high" ? "low" : "high");
    return end in spec ? spec[end] : spec.central;
  }
  function load(defaults, level = "central") {
    const perils = Object.entries(defaults.perils).map(([name, p]) => {
      const g = (k, dflt) => k in p ? pick(p[k], level) : dflt;
      return { name, label: p.label, rate: g("rate"), xm: g("xm"), alpha: g("alpha"), cap: g("cap"),
               attribution: g("attribution"), insurable: g("insurable"), common_mode: g("common_mode", 0),
               rate_cv: g("rate_cv", 0), payout_lag_years: g("payout_lag_years", 1) };
    });
    const s = { perils, members: Math.round(pick(defaults.members.count, level)), revenue: pick(defaults.members.revenue, level) };
    for (const section of ["structure", "pricing", "capital"])
      for (const [k, v] of Object.entries(defaults[section])) s[k] = pick(v, level);
    return s;
  }
  const severity = p => TP(p.xm, p.alpha, p.cap);
  const liableShare = p => p.attribution * p.insurable;
  function expectedClaim(p, limit) {
    const s = liableShare(p);
    return s > 0 ? p.rate * s * severity(p).layer(0, limit / s) : 0;
  }

  // ---- simulation of years (catmodel/model.py simulate)
  function simulate(s, nYears = 100000, seed = 1) {
    const r = rng(seed), m = s.members, L = s.per_event_limit, A = s.annual_aggregate;
    const harm = new Float64Array(nYears), liable = new Float64Array(nYears);
    const perMember = new Float64Array(nYears * m), raw = {};
    for (const p of s.perils) {
      const sev = severity(p), share = liableShare(p), k = p.rate_cv > 0 ? 1 / (p.rate_cv * p.rate_cv) : 0;
      const pc = new Float64Array(nYears * m);
      for (let y = 0; y < nYears; y++) {
        const lam = p.rate * (k ? r.gamma(k, 1 / k) : 1);
        const n = r.poisson(lam);
        for (let e = 0; e < n; e++) {
          const x = sev.quantile(r.u()), lia = x * share;
          harm[y] += x; liable[y] += lia;
          if (r.u() < p.common_mode) {
            const each = Math.min(lia / m, L);
            for (let j = 0; j < m; j++) pc[y * m + j] += each;
          } else {
            pc[y * m + Math.floor(r.u() * m)] += Math.min(lia, L);
          }
        }
      }
      raw[p.name] = pc;
      for (let i = 0; i < pc.length; i++) perMember[i] += pc[i];
    }
    return aggregate(s, { harm, liable, perMember, raw, n: nYears });
  }

  // per-member annual aggregates, allocated back to perils pro rata
  function aggregate(s, y) {
    const m = s.members, n = y.n, A = s.annual_aggregate;
    const claims = new Float64Array(n), byPeril = {};
    const scale = new Float64Array(n * m);
    for (let i = 0; i < n * m; i++) {
      const v = y.perMember[i], c = Math.min(v, A);
      scale[i] = v > 0 ? c / v : 1;
      claims[Math.floor(i / m)] += c;
    }
    for (const [name, pc] of Object.entries(y.raw)) {
      const out = new Float64Array(n);
      for (let i = 0; i < n * m; i++) out[Math.floor(i / m)] += pc[i] * scale[i];
      byPeril[name] = out;
    }
    return { harm: y.harm, liable: y.liable, claims, byPeril, n };
  }

  // ---- statistics on samples (numpy's default linear-interpolation quantile)
  const mean = x => { let t = 0; for (let i = 0; i < x.length; i++) t += x[i]; return t / x.length; };
  const sorted = x => Float64Array.from(x).sort();
  function qSorted(xs, p) {
    const h = (xs.length - 1) * p, lo = Math.floor(h), hi = Math.min(lo + 1, xs.length - 1);
    return xs[lo] + (h - lo) * (xs[hi] - xs[lo]);
  }
  function tvarSorted(xs, p) {
    const q = qSorted(xs, p);
    let t = 0, n = 0;
    for (let i = xs.length - 1; i >= 0 && xs[i] >= q; i--) { t += xs[i]; n++; }
    return n ? t / n : q;
  }

  // ---- layer stack, premium (catmodel/pricing.py)
  const layer = (x, attach, limit) => Math.min(Math.max(x - attach, 0), limit);
  function stack(s, y) {
    const n = y.n, c = y.claims;
    const re = new Float64Array(n), gov = new Float64Array(n), net = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      re[i] = s.reinsurance_limit > 0 ? layer(c[i], s.reinsurance_attach, s.reinsurance_limit) : 0;
      gov[i] = s.government_share > 0 ? s.government_share * Math.max(c[i] - re[i] - s.government_attach, 0) : 0;
      net[i] = c[i] - re[i] - gov[i];
    }
    const netSorted = sorted(net), elNet = mean(net);
    const scr = Math.max(qSorted(netSorted, 0.995) - elNet, 0);
    const riCost = s.catbond_multiple * mean(re);
    const premium = (elNet + riCost + s.cost_of_capital * scr) / (1 - s.expense_ratio);
    const resources = premium * (1 - s.expense_ratio) + s.paid_in_capital, callCap = s.members * s.callable_per_member;
    const calls = new Float64Array(n), unpaid = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      const gap = Math.max(net[i] - resources, 0);
      calls[i] = Math.min(gap, callCap);
      unpaid[i] = gap - calls[i];
    }
    return { claims: c, reinsured: re, government: gov, net, netSorted, premium, reinsurance_cost: riCost, scr, calls, unpaid };
  }

  // ---- reserves and capital (catmodel/reserves.py, capital_s2.py, capital_us.py)
  const unpaidFraction = lag => lag > 0 ? lag * (1 - Math.exp(-1 / lag)) : 0;
  function reserves(s, y, netShare) {
    let undisc = 0, disc = 0, lagW = 0;
    for (const p of s.perils) {
      const el = mean(y.byPeril[p.name]) * netShare, u = unpaidFraction(p.payout_lag_years);
      undisc += el * u; disc += el * u / (1 + s.discount_rate * p.payout_lag_years); lagW += el * u * p.payout_lag_years;
    }
    return { statutory: undisc, best_estimate: disc, duration: undisc ? lagW / undisc : 0 };
  }
  const MCR_ALPHA_BE = 0.103, MCR_BETA_PREMIUM = 0.131, RESERVE_SIGMA = 0.11;
  function solvency2(s, st, res) {
    const req = st.scr;
    const runoff = 3 * RESERVE_SIGMA * res.best_estimate;
    const rm = s.s2_coc * runoff * res.duration / (1 + s.discount_rate * res.duration);
    const linear = MCR_ALPHA_BE * res.best_estimate + MCR_BETA_PREMIUM * st.premium;
    const mcr = Math.min(Math.max(linear, 0.25 * req), 0.45 * req);
    const tier1 = s.paid_in_capital, tier2 = s.members * s.callable_per_member;
    const eligible = tier1 + Math.min(tier2, 0.5 * req, tier1);
    return { scr: req, mcr, best_estimate: res.best_estimate, risk_margin: rm, technical_provisions: res.best_estimate + rm,
             tier1, tier2_ancillary: tier2, eligible_own_funds_scr: eligible, eligible_own_funds_mcr: tier1,
             solvency_ratio: req ? eligible / req : Infinity, mcr_ratio: mcr ? tier1 / mcr : Infinity, tier1_covers_half_scr: tier1 >= 0.5 * req };
  }
  const US_LEVELS = [[2.0, "no action"], [1.5, "company action"], [1.0, "regulatory action"], [0.7, "authorized control"]];
  const actionLevel = ratio => (US_LEVELS.find(([t]) => ratio >= t) || [0, "mandatory control"])[1];
  function us(s, st, res) {
    const rPrem = s.us_premium_factor * st.premium, rRes = s.us_reserve_factor * res.statutory;
    const rCat = qSorted(st.netSorted, 0.99);
    const rbc = Math.sqrt(rPrem * rPrem + rRes * rRes + rCat * rCat), acl = 0.5 * rbc, tac = s.paid_in_capital;
    const ratio = acl ? tac / acl : Infinity;
    const need = Math.max(qSorted(st.netSorted, 0.996) - st.premium * (1 - s.expense_ratio), 0);
    return { statutory_reserves: res.statutory, r_premium: rPrem, r_reserve: rRes, r_cat: rCat, rbc, acl,
             total_adjusted_capital: tac, rbc_ratio: ratio, action_level: actionLevel(ratio),
             capital_for_996: need, rating_cover: need ? tac / need : Infinity };
  }

  // ---- cat bond on a layer of annual losses (catmodel/pricing.py catbond)
  const LANE = { gamma: 0.55, a: 0.49, b: 0.57 };
  function catbond(xs, attach, exhaust, multiple, wangLambda) {   // xs sorted ascending
    const limit = exhaust - attach, n = xs.length;
    const above = v => { let lo = 0, hi = n; while (lo < hi) { const mid = (lo + hi) >> 1; if (xs[mid] <= v) lo = mid + 1; else hi = mid; } return (n - lo) / n; };
    const pa = above(attach), pe = above(exhaust);
    let tot = 0; for (let i = 0; i < n; i++) tot += layer(xs[i], attach, limit);
    const el = tot / n / limit, cel = pa > 0 ? el / pa : 0;
    const lane = pa > 0 ? LANE.gamma * Math.pow(100 * pa, LANE.a) * Math.pow(100 * cel, LANE.b) / 100 : 0;
    let wang = 0, prev = null;
    for (let i = 0; i <= 400; i++) {
      const x = attach + limit * i / 400, sfv = above(x);
      const g = sfv > 0 && sfv < 1 ? ncdf(ninv(sfv) + wangLambda) : sfv;
      if (prev !== null) wang += (prev + g) / 2 * (limit / 400);
      prev = g;
    }
    return { attach, exhaust, prob_attach: pa, prob_exhaust: pe, expected_loss: el, spread_multiple: multiple * el,
             spread_lane: lane, spread_wang: wang / limit };
  }

  // ---- everything the page shows, from settings and simulated years
  function evaluate(s, y) {
    const st = stack(s, y), gross = mean(st.claims);
    const res = reserves(s, y, gross ? mean(st.net) / gross : 1);
    let pCalls = 0, pUnpaid = 0, unpaidSum = 0;
    for (let i = 0; i < y.n; i++) { if (st.calls[i] > 0) pCalls++; if (st.unpaid[i] > 0) { pUnpaid++; unpaidSum += st.unpaid[i]; } }
    const byPeril = {};
    for (const p of s.perils) byPeril[p.name] = { harm: p.rate * severity(p).mean(), liable: p.rate * severity(p).mean() * liableShare(p), claims: mean(y.byPeril[p.name]) };
    return { stack: st, s2: solvency2(s, st, res), us: us(s, st, res), reserves: res, byPeril,
             harm: mean(y.harm), liable: mean(y.liable), gross, net: mean(st.net),
             p_calls: pCalls / y.n, p_unpaid: pUnpaid / y.n, mean_unpaid: pUnpaid ? unpaidSum / pUnpaid : 0 };
  }

  const api = { TP, rng, ncdf, ninv, LEVELS, pick, load, expectedClaim, simulate, aggregate, stack, reserves,
                solvency2, us, catbond, evaluate, qSorted, tvarSorted, sorted, mean, unpaidFraction };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MaimModel = api;
})(typeof window !== "undefined" ? window : globalThis);
