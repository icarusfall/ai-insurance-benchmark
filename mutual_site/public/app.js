// Mutually Assured AI Modelling: the lever board, charts and tables. The model lives in model.js, data in data.js.
(function () {
  "use strict";
  const D = window.MAIM, M = window.MaimModel;
  const $ = s => document.querySelector(s);
  const el = (tag, attrs = {}, html = "") => { const e = document.createElement(tag); Object.assign(e, attrs); if (html) e.innerHTML = html; return e; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const N_YEARS = 100000, SEED = 1;
  const PERIL_COLOURS = { bio_misuse: "--s1", cyber_misuse: "--s2", agent_runaway: "--s3" };
  const sourceById = Object.fromEntries(D.sources.map(s => [s.id, s]));

  // ---- formatting
  const money = v => {
    if (!isFinite(v)) return "∞";
    const a = Math.abs(v);
    if (a >= 1000) return `$${(v / 1000).toLocaleString("en", { maximumFractionDigits: 1 })}tn`;
    if (a >= 10) return `$${v.toLocaleString("en", { maximumFractionDigits: 0 })}bn`;
    if (a >= 1) return `$${v.toFixed(2)}bn`;
    if (a >= 0.01) return `$${(v * 1000).toFixed(0)}m`;
    if (a >= 0.0001) return `$${(v * 1000).toFixed(1)}m`;
    return a === 0 ? "$0" : `$${(v * 1e6).toFixed(0)}k`;
  };
  const pct = (v, d) => {
    if (!isFinite(v)) return "∞";
    const a = Math.abs(v * 100);
    const digits = d !== undefined ? d : a >= 10 ? 0 : a >= 1 ? 1 : a >= 0.1 ? 2 : 3;
    return `${(v * 100).toFixed(digits)}%`;
  };
  const num = v => v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2);
  const ratePerYear = v => v >= 1 ? `${num(v)} a year` : `1 in ${Math.round(1 / v).toLocaleString("en")} years`;

  // ---- lever definitions
  const PERIL_LEVERS = [
    { key: "rate", label: "How often", scale: "log", min: 1e-4, max: 5, fmt: ratePerYear },
    { key: "alpha", label: "Tail index α (lower is fatter)", scale: "lin", min: 0.4, max: 2.5, step: 0.05, fmt: v => v.toFixed(2) },
    { key: "attribution", label: "Share of the harm pinned on the lab", scale: "log", min: 0.001, max: 1, fmt: v => pct(v) },
    { key: "insurable", label: "Share of that which is insurable", scale: "lin", min: 0, max: 1, step: 0.01, fmt: v => pct(v, 0) },
    { key: "common_mode", label: "Chance all members' models are to blame", scale: "lin", min: 0, max: 1, step: 0.01, fmt: v => pct(v, 0) },
  ];
  const GROUPS = [
    { title: "The mutual", section: "structure", levers: [
      { key: "members", label: "Member labs", scale: "int", min: 1, max: 12, spec: D.defaults.members.count, fmt: v => String(v) },
      { key: "revenue", label: "Revenue per member", scale: "log", min: 0.5, max: 200, spec: D.defaults.members.revenue, fmt: money },
      { key: "per_event_limit", label: "Cover per member per event", scale: "log", min: 0.05, max: 500, fmt: money },
      { key: "annual_aggregate", label: "Cover per member per year", scale: "log", min: 0.05, max: 1000, fmt: money },
      { key: "paid_in_capital", label: "Paid-in capital", scale: "log0", min: 0.1, max: 1000, fmt: money },
      { key: "callable_per_member", label: "Callable from each member", scale: "log0", min: 0.05, max: 200, fmt: money },
    ] },
    { title: "Above the mutual", section: "structure", levers: [
      { key: "reinsurance_attach", label: "Reinsurance or cat bond attaches at", scale: "log0", min: 0.05, max: 500, fmt: money },
      { key: "reinsurance_limit", label: "Reinsurance or cat bond limit", scale: "log0", min: 0.05, max: 500, fmt: money },
      { key: "government_attach", label: "Government steps in above", scale: "log0", min: 0.05, max: 1000, fmt: money },
      { key: "government_share", label: "Government share above that", scale: "lin", min: 0, max: 1, step: 0.05, fmt: v => pct(v, 0) },
    ] },
    { title: "Pricing", section: "pricing", levers: [
      { key: "cost_of_capital", label: "Return required on capital", scale: "lin", min: 0, max: 0.3, step: 0.005, fmt: v => pct(v, 1) },
      { key: "expense_ratio", label: "Expenses, share of premium", scale: "lin", min: 0, max: 0.4, step: 0.01, fmt: v => pct(v, 0) },
      { key: "catbond_multiple", label: "Reinsurance price, × expected loss", scale: "lin", min: 1, max: 20, step: 0.5, fmt: v => `${v}×` },
    ] },
  ];

  // slider position (0..1000) <-> value
  const toValue = (lv, t) => {
    t = +t;
    if (lv.scale === "log") return lv.min * Math.pow(lv.max / lv.min, t / 1000);
    if (lv.scale === "log0") return t === 0 ? 0 : lv.min * Math.pow(lv.max / lv.min, (t - 1) / 999);
    if (lv.scale === "int") return Math.round(t);
    const v = lv.min + (lv.max - lv.min) * t / 1000;
    return lv.step ? Math.round(v / lv.step) * lv.step : v;
  };
  const toPos = (lv, v) => {
    if (lv.scale === "log") return 1000 * Math.log(Math.max(v, lv.min) / lv.min) / Math.log(lv.max / lv.min);
    if (lv.scale === "log0") return v <= 0 ? 0 : 1 + 999 * Math.log(Math.max(v, lv.min) / lv.min) / Math.log(lv.max / lv.min);
    if (lv.scale === "int") return v;
    return 1000 * (v - lv.min) / (lv.max - lv.min);
  };

  // ---- state
  let level = "central", S = M.load(D.defaults, level), last = null, timer = null;
  const inputs = [];          // {lv, input, output, get, set}

  function basisHtml(spec) {
    if (!spec || typeof spec !== "object") return "";
    const chips = (spec.sources || []).map(id => sourceById[id]
      ? `<a class="chip" href="#src-${id}">${esc(id.replace(/_/g, " "))}</a>` : "").join("");
    const range = "low" in spec ? ` Range ${spec.low} to ${spec.high}.` : "";
    return `<details><summary></summary>${esc(spec.basis || "")}${range}<br>${chips}</details>`;
  }

  function addLever(container, lv, get, set, spec) {
    const id = `lv-${inputs.length}`;
    const row = el("div", { className: "lever" });
    row.innerHTML = `<label for="${id}">${esc(lv.label)}</label><output for="${id}"></output>
      <input type="range" id="${id}" min="${lv.scale === "int" ? lv.min : 0}" max="${lv.scale === "int" ? lv.max : 1000}" step="1">${basisHtml(spec)}`;
    container.appendChild(row);
    const input = row.querySelector("input"), output = row.querySelector("output");
    input.addEventListener("input", () => { set(toValue(lv, input.value)); output.textContent = lv.fmt(get()); markCustom(); schedule(); });
    inputs.push({ lv, input, output, get, set });
  }

  function buildLevers() {
    const panel = $("#levers-panel");
    panel.innerHTML = "";
    inputs.length = 0;
    S.perils.forEach((p, i) => {
      const fs = el("fieldset");
      fs.innerHTML = `<legend><i style="background:var(${PERIL_COLOURS[p.name] || "--s7"})"></i>${esc(p.label)}</legend>`;
      for (const lv of PERIL_LEVERS)
        addLever(fs, lv, () => S.perils[i][lv.key], v => { S.perils[i][lv.key] = v; }, D.defaults.perils[p.name][lv.key]);
      panel.appendChild(fs);
    });
    for (const g of GROUPS) {
      const fs = el("fieldset");
      fs.innerHTML = `<legend>${esc(g.title)}</legend>`;
      for (const lv of g.levers)
        addLever(fs, lv, () => S[lv.key], v => { S[lv.key] = v; }, lv.spec || D.defaults[g.section][lv.key]);
      panel.appendChild(fs);
    }
    syncLevers();
  }
  function syncLevers() {
    for (const { lv, input, output, get } of inputs) { input.value = toPos(lv, get()); output.textContent = lv.fmt(get()); }
  }
  function markCustom() {
    document.querySelectorAll(".presets button").forEach(b => b.setAttribute("aria-pressed", "false"));
  }
  document.querySelectorAll(".presets button").forEach(b => b.addEventListener("click", () => {
    level = b.dataset.level;
    S = M.load(D.defaults, level);
    document.querySelectorAll(".presets button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    syncLevers();
    schedule(0);
  }));

  function schedule(delay = 150) {
    clearTimeout(timer);
    timer = setTimeout(recompute, delay);
  }

  function recompute() {
    if (S.per_event_limit > S.annual_aggregate) S.annual_aggregate = S.per_event_limit;
    const y = M.simulate(S, N_YEARS, SEED);
    const r = M.evaluate(S, y);
    r.grossSorted = M.sorted(r.stack.claims);
    last = r;
    renderTiles(r); renderEP(r); renderFunnel(r); renderPerilTable(r); renderCapital(r); renderBond();
    syncLevers();
  }

  // ---- outputs
  function tile(label, value, sub, status) {
    return `<div class="tile"><div class="label">${label}</div><div class="value">${value}</div>
      ${status ? `<div class="status ${status[0]}">${status[1]}</div>` : ""}<div class="sub">${sub}</div></div>`;
  }
  function renderTiles(r) {
    const prem = r.stack.premium / S.members, share = prem / S.revenue;
    const s2 = r.s2, u = r.us;
    const s2s = s2.solvency_ratio >= 1.5 ? ["good", "comfortable"] : s2.solvency_ratio >= 1 ? ["warn", "covered, thinly"] : ["bad", "below the SCR"];
    const uss = u.action_level === "no action" ? ["good", "no action"] : u.action_level === "company action" ? ["warn", "company action"] : ["bad", u.action_level];
    $("#tiles").innerHTML =
      tile("Premium per member", money(prem), `${pct(share)} of ${money(S.revenue)} revenue`,
           share < 0.01 ? ["good", "a rounding error"] : share < 0.05 ? ["warn", "noticeable"] : ["bad", "a large bill"]) +
      tile("Share of expected harm the mutual pays", pct(r.gross / r.harm), `of ${money(r.harm)} a year in the world`) +
      tile("Solvency II ratio", pct(s2.solvency_ratio, 0), `SCR ${money(s2.scr)} · own funds ${money(s2.eligible_own_funds_scr)}`, s2s) +
      tile("US RBC ratio", pct(u.rbc_ratio, 0), `ACL ${money(u.acl)} · capital ${money(u.total_adjusted_capital)}`, uss) +
      tile("Years members get a call", pct(r.p_calls), "premium and paid-in capital not enough") +
      tile("Years claims go unpaid", pct(r.p_unpaid), r.p_unpaid ? `average shortfall ${money(r.mean_unpaid)}` : "never, in 100,000 years",
           r.p_unpaid === 0 ? ["good", "always paid"] : r.p_unpaid < 0.002 ? ["warn", "rarely short"] : ["bad", "often short"]);
  }

  // exceedance chart: x = return period (log), y = annual claims
  function renderEP(r) {
    const box = $("#ep-chart"), W = Math.max(box.clientWidth, 300), H = 260, ml = 52, mr = 14, mt = 12, mb = 34;
    const rpMin = 2, rpMax = 10000, n = 160;
    const netSorted = r.stack.netSorted, grossSorted = r.grossSorted;
    const rps = Array.from({ length: n }, (_, i) => rpMin * Math.pow(rpMax / rpMin, i / (n - 1)));
    const at = (xs, rp) => M.qSorted(xs, 1 - 1 / rp);
    const gross = rps.map(rp => at(grossSorted, rp)), net = rps.map(rp => at(netSorted, rp));
    const layered = S.reinsurance_limit > 0 || S.government_share > 0;
    const resources = r.stack.premium * (1 - S.expense_ratio) + S.paid_in_capital;
    const withCalls = resources + S.members * S.callable_per_member;
    const ymax = Math.max(...gross, withCalls * 1.05, 0.01) * 1.08;
    const X = rp => ml + (W - ml - mr) * Math.log(rp / rpMin) / Math.log(rpMax / rpMin);
    const Y = v => mt + (H - mt - mb) * (1 - Math.min(v, ymax) / ymax);
    const path = vals => vals.map((v, i) => `${i ? "L" : "M"}${X(rps[i]).toFixed(1)},${Y(v).toFixed(1)}`).join("");
    const ticksY = niceTicks(ymax, 4);
    let svg = `<svg width="${W}" height="${H}" role="img" aria-label="annual claims by return period">`;
    const tickMoney = v => money(v).replace(/\.00(?=bn)/, "");
    for (const t of ticksY) svg += `<line x1="${ml}" x2="${W - mr}" y1="${Y(t)}" y2="${Y(t)}" stroke="var(--grid)"/><text x="${ml - 6}" y="${Y(t) + 4}" text-anchor="end">${tickMoney(t)}</text>`;
    const rpTicks = W < 520 ? [10, 100, 10000] : [2, 10, 100, 1000, 10000];
    for (const rp of rpTicks) {
      const anchor = rp === 10000 ? "end" : rp === 2 ? "start" : "middle";
      svg += `<line x1="${X(rp)}" x2="${X(rp)}" y1="${mt}" y2="${H - mb}" stroke="var(--grid)"/><text x="${X(rp)}" y="${H - mb + 16}" text-anchor="${anchor}">1 in ${rp.toLocaleString("en")}</text>`;
    }
    svg += `<text x="${(ml + W - mr) / 2}" y="${H - 2}" text-anchor="middle">years</text>`;
    const ref = (v, label) => v < ymax ? `<line x1="${ml}" x2="${W - mr}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--ink-2)" stroke-dasharray="4 3" stroke-width="1.2"/><text class="halo" x="${W - mr - 4}" y="${Y(v) - 5}" text-anchor="end">${label} ${money(v)}</text>` : "";
    if (layered) svg += `<path d="${path(net)}" fill="none" stroke="var(--s2)" stroke-width="2"/>`;
    svg += `<path d="${path(gross)}" fill="none" stroke="var(--s1)" stroke-width="2"/>`;
    svg += ref(resources, "premium + paid-in");
    if (S.callable_per_member > 0) svg += ref(withCalls, "+ member calls");
    svg += `<line id="ep-x" y1="${mt}" y2="${H - mb}" stroke="var(--axis)" visibility="hidden"/>`;
    svg += `<rect x="${ml}" y="${mt}" width="${W - ml - mr}" height="${H - mt - mb}" fill="transparent" id="ep-hit"/></svg>`;
    box.innerHTML = svg;
    $("#ep-legend").innerHTML = `<span><i style="background:var(--s1)"></i>mutual's claims</span>` +
      (layered ? `<span><i style="background:var(--s2)"></i>after reinsurance and government</span>` : "") +
      `<span><i class="dash"></i>what pays for it</span>`;
    const tip = $("#ep-tip"), hit = $("#ep-hit"), xline = $("#ep-x");
    hit.addEventListener("mousemove", e => {
      const rect = hit.getBoundingClientRect(), px = e.clientX - rect.left;
      const rp = rpMin * Math.pow(rpMax / rpMin, px / rect.width);
      xline.setAttribute("x1", X(rp)); xline.setAttribute("x2", X(rp)); xline.setAttribute("visibility", "visible");
      tip.style.display = "block";
      tip.innerHTML = `<b>1 in ${Math.round(rp).toLocaleString("en")} years</b><br>claims ${money(at(grossSorted, rp))}` +
        (layered ? `<br>after layers ${money(at(netSorted, rp))}` : "");
      const fig = box.parentElement.getBoundingClientRect();
      tip.style.left = `${Math.min(e.clientX - fig.left + 12, fig.width - 170)}px`;
      tip.style.top = `${e.clientY - fig.top - 10}px`;
    });
    hit.addEventListener("mouseleave", () => { tip.style.display = "none"; xline.setAttribute("visibility", "hidden"); });
  }
  function niceTicks(max, count) {
    const raw = max / count, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw);
    const out = [];
    for (let t = 0; t <= max + 1e-12; t += step) out.push(+t.toPrecision(10));
    return out;
  }

  // where expected harm goes: log bars
  function renderFunnel(r) {
    const rows = [["Harm in the world", r.harm], ["Insurable liability pinned on labs", r.liable], ["Paid by the mutual", r.gross]];
    if (S.reinsurance_limit > 0 || S.government_share > 0) rows.push(["Kept by the mutual after layers", r.net]);
    const box = $("#funnel"), W = Math.max(box.clientWidth, 280), narrow = W < 520;
    const rowH = narrow ? 44 : 30, lw = narrow ? 0 : Math.min(250, W * 0.45), H = rows.length * rowH + 6;
    const lo = 1e-4, hi = Math.max(r.harm, 1) * 1.5;
    const X = v => (W - lw - 70) * Math.log(Math.max(v, lo) / lo) / Math.log(hi / lo);
    let svg = `<svg width="${W}" height="${H}" role="img" aria-label="expected harm from world to mutual">`;
    rows.forEach(([label, v], i) => {
      const y = i * rowH + 4, w = Math.max(X(v), 2), by = narrow ? y + 18 : y + 4;
      svg += `<text x="0" y="${y + 13}">${label}</text><rect x="${lw}" y="${by}" width="${w}" height="16" rx="4" fill="var(--s7)" opacity="${1 - i * 0.18}"/>` +
             `<text x="${lw + w + 6}" y="${by + 13}" style="fill:var(--ink)">${money(v)}</text>`;
    });
    box.innerHTML = svg + "</svg>";
  }

  function renderPerilTable(r) {
    const total = r.gross || 1;
    $("#peril-table").innerHTML = `<thead><tr><th>Peril, expected per year</th><th class="num">Harm in the world</th><th class="num">Insurable lab liability</th><th class="num">Mutual pays</th><th class="num">Share of claims</th></tr></thead><tbody>` +
      S.perils.map(p => { const b = r.byPeril[p.name]; return `<tr><td><i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:var(${PERIL_COLOURS[p.name]});margin-right:6px"></i>${esc(p.label)}</td>
        <td class="num">${money(b.harm)}</td><td class="num">${money(b.liable)}</td><td class="num">${money(b.claims)}</td><td class="num">${pct(b.claims / total, 0)}</td></tr>`; }).join("") +
      `<tr><td><b>All</b></td><td class="num"><b>${money(r.harm)}</b></td><td class="num"><b>${money(r.liable)}</b></td><td class="num"><b>${money(r.gross)}</b></td><td class="num">100%</td></tr></tbody>`;
  }

  function renderCapital(r) {
    const s2 = r.s2, u = r.us, st = r.stack, m = S.members;
    const kv = rows => `<dl class="kv">${rows.map(([k, v, cls]) => `<dt class="${cls || ""}">${k}</dt><dd class="${cls || ""}">${v}</dd>`).join("")}</dl>`;
    const capitalCharge = S.cost_of_capital * st.scr, expenses = st.premium * S.expense_ratio;
    $("#capital-cards").innerHTML =
      `<div class="card"><h3>The premium <small>whole mutual, per year</small></h3>${kv([
        ["Expected claims kept", money(r.net)], ["Reinsurance or cat bond", money(st.reinsurance_cost)],
        [`Cost of capital, ${pct(S.cost_of_capital, 1)} × SCR`, money(capitalCharge)], [`Expenses, ${pct(S.expense_ratio, 0)}`, money(expenses)],
        ["Premium", money(st.premium), "total"], [`Per member (${m})`, money(st.premium / m), "total"]])}</div>` +
      `<div class="card"><h3>Solvency II <small>99.5% over one year</small></h3>${kv([
        ["SCR", money(s2.scr)], ["MCR", money(s2.mcr)], ["Best estimate of claims owed", money(s2.best_estimate)],
        ["Risk margin", money(s2.risk_margin)], ["Tier 1: paid-in capital", money(s2.tier1)],
        ["Tier 2: callable from members", money(s2.tier2_ancillary)], ["Eligible for the SCR", money(s2.eligible_own_funds_scr), "total"],
        ["SCR ratio", pct(s2.solvency_ratio, 0), "total"], ["MCR ratio (tier 1 only)", pct(s2.mcr_ratio, 0), "total"]])}</div>` +
      `<div class="card"><h3>US statutory <small>RBC-style</small></h3>${kv([
        ["Premium risk charge", money(u.r_premium)], ["Reserve risk charge", money(u.r_reserve)],
        ["Catastrophe charge (1-in-100 year)", money(u.r_cat)], ["RBC", money(u.rbc)], ["Authorized control level", money(u.acl)],
        ["Surplus (calls not admitted)", money(u.total_adjusted_capital)], ["RBC ratio", pct(u.rbc_ratio, 0), "total"],
        ["Regulator's response", u.action_level, "total"], ["Statutory reserves", money(u.statutory_reserves)],
        ["Capital for a 1-in-250 year", money(u.capital_for_996)]])}</div>`;
  }

  function renderBond() {
    if (!last) return;
    let a = +$("#bond-attach").value, x = +$("#bond-exhaust").value;
    if (!(x > a)) x = a + 1;
    const b = M.catbond(last.grossSorted, a, x, S.catbond_multiple, S.wang_lambda);
    $("#bond-tiles").innerHTML =
      tile("Chance it loses anything", pct(b.prob_attach), `attaches above ${money(a)}`) +
      tile("Chance it is wiped out", pct(b.prob_exhaust), `exhausts at ${money(x)}`) +
      tile("Expected loss", pct(b.expected_loss), "of principal, per year") +
      tile(`Spread at ${S.catbond_multiple}× expected loss`, pct(b.spread_multiple), "the reinsurance price lever") +
      tile("Lane (2000) spread", pct(b.spread_lane), "from attach and conditional loss") +
      tile("Wang transform spread", pct(b.spread_wang), `λ = ${S.wang_lambda}`);
  }
  $("#bond-attach").addEventListener("input", renderBond);
  $("#bond-exhaust").addEventListener("input", renderBond);

  // ---- bio insurability tables (computed in Python by catmodel.insurability)
  function renderBio() {
    $("#bio-table").innerHTML = `<thead><tr><th>Criterion</th><th>Test</th><th>Result</th><th>Verdict</th><th>What would make it pass</th></tr></thead><tbody>` +
      D.bio.criteria.map(c => `<tr><td><b>${esc(c.criterion)}</b></td><td>${esc(c.test)}</td><td>${esc(c.result)}</td>
        <td class="verdict ${esc(c.verdict)}">${esc(c.verdict)}</td><td>${esc(c.fix)}</td></tr>`).join("") + "</tbody>";
    $("#bio-grid").innerHTML = `<thead><tr><th class="num">α</th><th class="num">Attribution</th><th class="num">Limit per member</th><th class="num">Expected claims</th>
      <th class="num">Share of lab liability paid</th><th class="num">Premium, % of revenue</th><th class="num">VaR 99.5%</th><th class="num">TVaR 99.5%</th></tr></thead><tbody>` +
      D.bio.grid.map(g => `<tr><td class="num">${g.alpha}</td><td class="num">${pct(g.attribution)}</td><td class="num">${money(g.limit)}</td>
        <td class="num">${money(g.el)}</td><td class="num">${pct(g.share_of_liability)}</td><td class="num">${pct(g.premium_share_revenue, 2)}</td>
        <td class="num">${money(g.var995)}</td><td class="num">${money(g.tvar995)}</td></tr>`).join("") + "</tbody>";
  }

  // ---- sources
  const LENSES = [["all", "All"], ["scratch", "First principles"], ["parallel", "Parallels"], ["market", "Markets"], ["expert", "Experts"]];
  function renderSources(lens = "all") {
    const tabs = $("#lens-tabs");
    tabs.innerHTML = LENSES.map(([k, l]) => `<button type="button" role="tab" data-lens="${k}" aria-selected="${k === lens}">${l}</button>`).join("");
    tabs.querySelectorAll("button").forEach(b => b.addEventListener("click", () => renderSources(b.dataset.lens)));
    const lensName = Object.fromEntries(LENSES);
    $("#source-list").innerHTML = D.sources.filter(s => lens === "all" || s.lens === lens).map(s => {
      const src = s.source || {};
      return `<div class="src" id="src-${esc(s.id)}"><h4>${esc(s.id.replace(/_/g, " "))}</h4>
        <span class="badge ${esc(s.status)}">${esc(s.status)}</span><span class="badge lens">${esc(lensName[s.lens] || s.lens)}</span>
        <span class="meta">${esc(s.peril)} · informs ${esc((s.informs || []).join(", "))}</span>
        <p>${esc(s.claim)}</p>
        <p class="meta"><a href="${esc(src.url)}" rel="noopener">${esc(src.title || src.url)}</a>${src.author ? ", " + esc(src.author) : ""}${src.publisher ? ", " + esc(src.publisher) : ""}${src.date ? ", " + esc(src.date) : ""}. Read ${esc(s.accessed)}.</p>
        ${s.caveats ? `<p class="meta">Caveats: ${esc(s.caveats)}</p>` : ""}</div>`;
    }).join("");
  }

  $("#built").textContent = D.built;
  buildLevers();
  renderBio();
  renderSources();
  recompute();
  window.addEventListener("resize", () => { if (last) { renderEP(last); renderFunnel(last); } });
})();
