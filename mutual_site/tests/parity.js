// Parity harness: reads a JSON request on stdin, runs the browser model, writes JSON to stdout.
// Driven by tests/test_mutual_site.py.
const M = require("../public/model.js");

const strip = r => {
  const out = {};
  for (const [k, v] of Object.entries(r)) if (!(v instanceof Float64Array) && k !== "stack") out[k] = v;
  return out;
};

let input = "";
process.stdin.on("data", d => { input += d; });
process.stdin.on("end", () => {
  const req = JSON.parse(input), s = req.settings;
  let out;
  if (req.op === "closed") {
    out = req.cases.map(c => {
      const d = M.TP(c.xm, c.alpha, c.cap);
      return { sf: c.xs.map(d.sf), layer: c.layers.map(([r, l]) => d.layer(r, l)), quantile: c.ps.map(d.quantile), mean: d.mean() };
    });
  } else if (req.op === "evaluate") {
    const y = req.years, n = y.claims.length;
    const years = { n, harm: Float64Array.from(y.harm), liable: Float64Array.from(y.liable), claims: Float64Array.from(y.claims), byPeril: {} };
    for (const [k, v] of Object.entries(y.by_peril)) years.byPeril[k] = Float64Array.from(v);
    const r = M.evaluate(s, years);
    out = { premium: r.stack.premium, scr: r.stack.scr, s2: r.s2, us: r.us, reserves: r.reserves,
            p_calls: r.p_calls, p_unpaid: r.p_unpaid,
            bond: M.catbond(M.sorted(years.claims), req.bond[0], req.bond[1], s.catbond_multiple, s.wang_lambda),
            expected_claim: s.perils.map(p => M.expectedClaim(p, s.per_event_limit)) };
  } else if (req.op === "simulate") {
    const y = M.simulate(s, req.n_years, req.seed);
    out = { claims: M.mean(y.claims), harm: M.mean(y.harm), liable: M.mean(y.liable),
            by_peril: Object.fromEntries(Object.entries(y.byPeril).map(([k, v]) => [k, M.mean(v)])) };
  } else if (req.op === "trajectory") {
    const c = M.loadCapability(req.defaults, req.level);
    out = { capability: c, paths: Object.fromEntries(M.TRAJECTORIES.map(t => [t, {
      horizons: req.dates.map(d => M.horizon(c, t, d)),
      years: Array.from({ length: c.last_year - c.first_year + 1 }, (_, i) => M.multipliers(c, t, c.first_year + i)) }])) };
  } else if (req.op === "preset") {
    const r = M.applyPreset(M.load(req.defaults, "central"), M.loadCapability(req.defaults, "central"), req.preset);
    out = { settings: r.s, capability: r.c };
  } else if (req.op === "load") {
    out = M.load(req.defaults, req.level);
  }
  process.stdout.write(JSON.stringify(out, (k, v) => v === Infinity ? "inf" : v));
});
