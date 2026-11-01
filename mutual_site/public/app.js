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
  const ratePerYear = v => v >= 1 || 1 / v < 1.5 ? `${num(v)} a year` : `1 in ${Math.round(1 / v).toLocaleString("en")} years`;

  // ---- lever definitions
  const PERIL_LEVERS = [
    { key: "xm", label: "Smallest event counted", scale: "log", min: 0.001, max: 10000, fmt: money },
    { key: "rate", label: "How often", scale: "log", min: 1e-4, max: 5, fmt: ratePerYear,
      note: p => `Events of at least ${money(p.xm)}. Lowering the threshold without raising this makes big events rarer.` },
    { key: "alpha", label: "Tail index α (lower is fatter)", scale: "lin", min: 0.4, max: 2.5, step: 0.05, fmt: v => v.toFixed(2),
      note: p => { const t = M.TP(p.xm, p.alpha, p.cap);
        return `Half of events cost more than ${money(t.quantile(0.5))}; one in ten more than ${money(t.quantile(0.9))}; one in a hundred more than ${money(t.quantile(0.99))}.`; } },
    { key: "attribution", label: "Share of the harm pinned on the lab", scale: "log", min: 0.001, max: 1, fmt: v => pct(v) },
    { key: "insurable", label: "Share of that which is insurable", scale: "lin", min: 0, max: 1, step: 0.01, fmt: v => pct(v, 0) },
    { key: "common_mode", label: "Chance all members' models are to blame", scale: "lin", min: 0, max: 1, step: 0.01, fmt: v => pct(v, 0) },
  ];
  const GROUPS = [
    { title: "The cover", section: "structure", levers: [
      { key: "members", label: "Labs covered", scale: "int", min: 1, max: 12, spec: D.defaults.members.count, fmt: v => String(v) },
      { key: "revenue", label: "Revenue per lab", scale: "log", min: 0.5, max: 200, spec: D.defaults.members.revenue, fmt: money },
      { key: "per_event_limit", label: "Cover each lab buys, per event", scale: "log", min: 0.05, max: 500, fmt: money },
      { key: "annual_aggregate", label: "Cover each lab buys, per year", scale: "log", min: 0.05, max: 1000, fmt: money,
        note: s => `The carrier can owe up to ${money(s.members * s.annual_aggregate)} a year across ${s.members} labs.` },
      { key: "paid_in_capital", label: "Carrier's paid-in capital", scale: "log0", min: 0.1, max: 1000, fmt: money },
      { key: "callable_per_member", label: "Callable from each lab (a mutual only)", scale: "log0", min: 0.05, max: 200, fmt: money },
    ] },
    { title: "Above the first carrier", section: "structure", levers: [
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

  function addLever(container, lv, get, set, spec, note) {
    const id = `lv-${inputs.length}`;
    const row = el("div", { className: "lever" });
    row.innerHTML = `<label for="${id}">${esc(lv.label)}</label><output for="${id}"></output>
      <input type="range" id="${id}" min="${lv.scale === "int" ? lv.min : 0}" max="${lv.scale === "int" ? lv.max : 1000}" step="1">${note ? `<p class="lever-note"></p>` : ""}${basisHtml(spec)}`;
    container.appendChild(row);
    const input = row.querySelector("input"), output = row.querySelector("output"), noteEl = row.querySelector(".lever-note");
    input.addEventListener("input", () => { set(toValue(lv, input.value)); output.textContent = lv.fmt(get()); syncNotes(); markCustom(); schedule(); });
    inputs.push({ lv, input, output, get, set, note, noteEl });
  }

  function buildLevers() {
    const panel = $("#levers-panel");
    panel.innerHTML = "";
    inputs.length = 0;
    S.perils.forEach((p, i) => {
      const fs = el("fieldset");
      fs.innerHTML = `<legend><i style="background:var(${PERIL_COLOURS[p.name] || "--s7"})"></i>${esc(p.label)}</legend>`;
      for (const lv of PERIL_LEVERS) {
        const l = lv.key === "xm" ? { ...lv, max: Math.min(lv.max, p.cap / 10) } : lv;   // the threshold stays below the cap
        addLever(fs, l, () => S.perils[i][lv.key], v => { S.perils[i][lv.key] = v; }, D.defaults.perils[p.name][lv.key],
                 lv.note && (() => lv.note(S.perils[i])));
      }
      panel.appendChild(fs);
    });
    for (const g of GROUPS) {
      const fs = el("fieldset");
      fs.innerHTML = `<legend>${esc(g.title)}</legend>`;
      for (const lv of g.levers)
        addLever(fs, lv, () => S[lv.key], v => { S[lv.key] = v; }, lv.spec || D.defaults[g.section][lv.key],
                 lv.note && (() => lv.note(S)));
      panel.appendChild(fs);
    }
    syncLevers();
  }
  function syncLevers() {
    for (const { lv, input, output, get } of inputs) { input.value = toPos(lv, get()); output.textContent = lv.fmt(get()); }
    syncNotes();
  }
  function syncNotes() {
    for (const { note, noteEl } of inputs) if (note) noteEl.textContent = note();
  }
  function markCustom() {
    document.querySelectorAll(".presets button").forEach(b => b.setAttribute("aria-pressed", "false"));
  }
  document.querySelectorAll(".presets button").forEach(b => b.addEventListener("click", () => {
    usePreset(b.dataset.level);
  }));

  function usePreset(name) {
    level = name === "market" ? "central" : name;
    S = M.load(D.defaults, level);
    C = M.loadCapability(D.defaults, level);
    chainOver = {}; legalOver = {}; legalScenario = name === "central" ? "central" : null;
    if (name === "market") { method = "expert"; ({ s: S, c: C } = M.applyPreset(S, C, D.markets.preset)); }
    else if (method !== "expert") applyMethod();
    renderMethodTabs();
    document.querySelectorAll(".presets button").forEach(x => x.setAttribute("aria-pressed", String(x.dataset.level === name)));
    syncLevers();
    schedule(0);
  }

  function schedule(delay = 150) {
    clearTimeout(timer);
    timer = setTimeout(recompute, delay);
  }

  function recompute() {
    if (S.per_event_limit > S.annual_aggregate) S.annual_aggregate = S.per_event_limit;
    const y = M.simulate(S, N_YEARS, SEED);
    const r = M.evaluate(S, y);
    r.grossSorted = M.sorted(r.stack.claims);
    r.liableSorted = M.sorted(y.liable);
    last = r;
    renderTiles(r); renderEP(r); renderFunnel(r); renderPerilTable(r); renderCapital(r); renderBond(); renderTrajectory(); renderFrequency(); renderLegal();
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
    const lvl = u.action_level_with_cat, uss = [lvl === "no action" ? "good" : lvl === "company action" ? "warn" : "bad", `with an AI charge: ${lvl}`];
    $("#tiles").innerHTML =
      tile("Premium per lab", money(prem), `${pct(share)} of ${money(S.revenue)} revenue`,
           share < 0.01 ? ["good", "a rounding error"] : share < 0.05 ? ["warn", "noticeable"] : ["bad", "a large bill"]) +
      tile("Share of expected harm the cover pays", pct(r.gross / r.harm), `of ${money(r.harm)} a year in the world`) +
      tile("Solvency II ratio", pct(s2.solvency_ratio, 0), `SCR ${money(s2.scr)} · own funds ${money(s2.eligible_own_funds_scr)}`, s2s) +
      tile("US RBC ratio, as written", pct(u.rbc_ratio, 0), `${pct(u.rbc_ratio_with_cat, 0)} if the 1-in-100 AI loss were charged like a hurricane`, uss) +
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
    const perLab = Math.min(S.per_event_limit, S.annual_aggregate), common = S.perils.some(p => p.common_mode > 0);
    const oneEvent = common ? S.members * perLab : perLab, oneYear = S.members * S.annual_aggregate;
    const lia1000 = M.qSorted(r.liableSorted, 0.999);
    const money1 = v => v >= 10 && v < 100 ? `$${v.toFixed(1)}bn` : money(v);   // so $10.2bn held vs $10bn owed reads right
    $("#ep-note").innerHTML = `<b>Why the line flattens.</b> The cover, not the capital, sets the ceiling. One event costs the carrier at most ` +
      `${money(oneEvent)}${common ? ` (${S.members} labs' ${money(perLab)} limits, when every lab's model is to blame)` : ""}, and a year at most ` +
      `${money1(oneYear)}. It holds ${money1(withCalls)}${S.callable_per_member > 0 ? " with member calls" : ""}, so it ${withCalls >= oneYear ? "can always pay" : "can run out in the worst years"}. ` +
      `Anything above the limits stays with the labs: on average ${pct(1 - r.gross / r.liable)} of what courts would make them pay is uninsured, ` +
      `and in a 1-in-1,000 year their liability is ${money(lia1000)} against ${money1(oneYear)} of cover. The insurer's stake ends where its limits end.`;
    $("#ep-legend").innerHTML = `<span><i style="background:var(--s1)"></i>carrier's claims</span>` +
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

  // where expected harm goes: log bars by default, linear to show true proportions
  let funnelScale = "log";
  function renderFunnel(r) {
    const log = funnelScale === "log";
    $("#funnel-scale-note").textContent = log
      ? "Log scale: each step down is a fall of orders of magnitude."
      : "Linear scale: bars at true size, so the smaller ones all but vanish.";
    const rows = [["Harm in the world", r.harm], ["Insurable liability pinned on labs", r.liable], ["Paid by the insurer", r.gross]];
    if (S.reinsurance_limit > 0 || S.government_share > 0) rows.push(["Kept by the insurer after layers", r.net]);
    const box = $("#funnel"), W = Math.max(box.clientWidth, 280), narrow = W < 520;
    const rowH = narrow ? 44 : 30, lw = narrow ? 0 : Math.min(250, W * 0.45), H = rows.length * rowH + 6;
    const lo = 1e-4, hi = Math.max(r.harm, 1) * 1.5;
    const X = log ? v => (W - lw - 70) * Math.log(Math.max(v, lo) / lo) / Math.log(hi / lo)
                  : v => (W - lw - 70) * Math.max(v, 0) / Math.max(r.harm, 1e-9);
    let svg = `<svg width="${W}" height="${H}" role="img" aria-label="expected harm from world to mutual">`;
    rows.forEach(([label, v], i) => {
      const y = i * rowH + 4, w = Math.max(X(v), 2), by = narrow ? y + 18 : y + 4;
      svg += `<text x="0" y="${y + 13}">${label}</text><rect x="${lw}" y="${by}" width="${w}" height="16" rx="4" fill="var(--s7)" opacity="${1 - i * 0.18}"/>` +
             `<text x="${lw + w + 6}" y="${by + 13}" style="fill:var(--ink)">${money(v)}</text>`;
    });
    box.innerHTML = svg + "</svg>";
  }

  // one unit ($m) for every money column, so the gap between columns shows in the digit count
  const millions = v => {
    const m = v * 1000;
    if (!isFinite(m)) return "∞";
    if (m === 0) return "0";
    if (m < 0.1) return "&lt;0.1";
    return m.toLocaleString("en", { maximumFractionDigits: m >= 10 ? 0 : 1, minimumFractionDigits: m >= 10 ? 0 : 1 });
  };

  function renderPerilTable(r) {
    // rows give exact expected harm and liability, but r.harm and r.liable are simulated means, so the total is
    // the sum of the rows to make the columns add up
    const parts = S.perils.map(p => r.byPeril[p.name]), sum = k => parts.reduce((t, b) => t + b[k], 0);
    const all = { harm: sum("harm"), liable: sum("liable"), claims: r.gross };
    const harmTotal = all.harm || 1, claimTotal = r.gross || 1;
    const row = (label, b, bold) => {
      const w = s => bold ? `<b>${s}</b>` : s;
      return `<tr><td>${label}</td><td class="num">${w(millions(b.harm))}</td><td class="num">${pct(b.harm / harmTotal)}</td>
        <td class="num">${w(millions(b.liable))}</td><td class="num">${w(millions(b.claims))}</td><td class="num">${pct(b.claims / claimTotal)}</td>
        <td class="num">${b.harm > 0 ? pct(b.claims / b.harm) : "–"}</td></tr>`;
    };
    $("#peril-table").innerHTML = `<thead><tr><th>Peril, expected per year</th><th class="num">Harm in the world, $m</th><th class="num">Share of all harm</th>` +
      `<th class="num">Insurable lab liability, $m</th><th class="num">Insurer pays, $m</th><th class="num">Share of all claims</th><th class="num">Insurer pays as share of harm</th></tr></thead><tbody>` +
      S.perils.map(p => row(`<i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:var(${PERIL_COLOURS[p.name]});margin-right:6px"></i>${esc(p.label)}`, r.byPeril[p.name])).join("") +
      row("<b>All</b>", all, true) + `</tbody>`;
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
      `<div class="card"><h3>US statutory <small>NAIC RBC, 2024 factors</small></h3>${kv([
        ["Statutory reserves", money(u.statutory_reserves)], [`Reserve risk, ${pct(u.reserve_factor, 0)} of reserves`, money(u.r_reserve)],
        [`Premium risk, ${pct(u.premium_factor, 1)} of premium`, money(u.r_premium)], ["Catastrophe risk (AI is not a listed peril)", money(0)],
        ["Authorized control level, with 3% operational risk", money(u.acl)], ["Surplus (calls not admitted)", money(u.total_adjusted_capital)],
        ["RBC ratio as written", pct(u.rbc_ratio, 0), "total"],
        ["If the 1-in-100 AI loss were charged like a hurricane", money(u.r_cat)], ["Authorized control level then", money(u.acl_with_cat)],
        ["RBC ratio then", pct(u.rbc_ratio_with_cat, 0), "total"], ["Regulator's response then", u.action_level_with_cat, "total"],
        ["Capital for a 1-in-250 year (rating view)", money(u.capital_for_996)]])}</div>`;
    $("#us-line").value = S.us_line;
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
      tile("Lane spread, priced like cyber", pct(b.spread_lane), `re-fit to 2023–26 bonds; ${pct(b.spread_lane_natcat)} if priced like nat cat`) +
      tile("Wang transform spread", pct(b.spread_wang), `λ = ${S.wang_lambda}`);
  }
  $("#bond-attach").addEventListener("input", renderBond);
  $("#bond-exhaust").addEventListener("input", renderBond);

  // ---- capability over time (catmodel/trajectory.py)
  const TRAJ_LABELS = { ai2027: "AI 2027", metr_2023: "METR trend since 2023", metr_long_run: "METR long-run trend", plateau: "Plateau" };
  const TRAJ_COLOURS = { ai2027: "--s2", metr_2023: "--s1", metr_long_run: "--s3", plateau: "--s4" };
  const TRAJ_YEARS = 20000;
  const PERIL_SHORT = { bio_misuse: "Bio", cyber_misuse: "Cyber", agent_runaway: "Agents" };
  const hours = v => !isFinite(v) ? "∞" : v < 100 ? `${num(v)} hours` : v < 2000 ? `${Math.round(v).toLocaleString("en")} hours` : `${(v / 2000).toLocaleString("en", { maximumFractionDigits: v < 20000 ? 1 : 0 })} work-years`;
  const hoursShort = v => !isFinite(v) ? "∞" : v < 1000 ? `${num(v)}h` : v < 1e6 ? `${(v / 1000).toFixed(v < 1e4 ? 1 : 0)}k h` : "> 1m h";
  const CAP_LEVERS = [
    { key: "ai2027_pace", label: "AI 2027: pace of reality", scale: "lin", min: 0.3, max: 1.2, step: 0.05, fmt: v => `${Math.round(v * 100)}% of AI 2027` },
    { key: "plateau_ceiling_hours", label: "Plateau: ceiling", scale: "log", min: 20, max: 10000, fmt: hours },
    { key: "stop_hours", label: "Stop the model at a horizon of", scale: "log", min: 50, max: 100000, fmt: hours },
    { key: "revenue_growth", label: "Members' revenue growth", scale: "lin", min: 1, max: 7, step: 0.25, fmt: v => `${v}× a year` },
  ];
  let C = M.loadCapability(D.defaults, level), traj = C.trajectory;

  function buildTrajLevers() {
    const panel = $("#traj-levers");
    panel.innerHTML = "";
    const fs = el("fieldset");
    fs.innerHTML = "<legend>The path</legend>";
    for (const lv of CAP_LEVERS) addLever(fs, lv, () => C[lv.key], v => { C[lv.key] = v; }, D.defaults.capability[lv.key]);
    panel.appendChild(fs);
    const fe = el("fieldset");
    fe.innerHTML = "<legend>How each peril responds</legend>";
    for (const p of S.perils) {
      const lv = { key: p.name, label: `${p.label}: elasticity`, scale: "lin", min: 0, max: 1.5, step: 0.05,
                   fmt: v => `${v.toFixed(2)}, capped at ${C.cap_multiple[p.name]}×` };
      addLever(fe, lv, () => C.elasticity[p.name], v => { C.elasticity[p.name] = v; }, D.defaults.capability.elasticity[p.name]);
    }
    panel.appendChild(fe);
    syncLevers();
  }
  function renderTrajTabs() {
    const tabs = $("#traj-tabs");
    tabs.innerHTML = M.TRAJECTORIES.map(t => `<button type="button" role="tab" data-traj="${t}" aria-selected="${t === traj}">${TRAJ_LABELS[t]}</button>`).join("");
    tabs.querySelectorAll("button").forEach(b => b.addEventListener("click", () => { traj = b.dataset.traj; renderTrajTabs(); renderTrajectory(); }));
  }

  const span = (a, b, f, sep = " → ") => a === b || f(a) === f(b) ? f(a) : `${f(a)}${sep}${f(b)}`;
  function renderTrajectory() {
    const rows = M.project(S, C, traj, TRAJ_YEARS, SEED);
    const live = rows.filter(r => !r.stopped), first = live[0], lastLive = live[live.length - 1];
    const stopRow = rows.find(r => r.stopped);
    const minRatio = live.length ? Math.min(...live.map(r => r.solvency_ratio)) : NaN;
    $("#traj-tiles").innerHTML =
      tile("Years before the stop", String(live.length), live.length ? span(first.year, lastLive.year, String, "–") : `the horizon passes ${hours(C.stop_hours)} by mid-${C.first_year}`,
           live.length >= 5 ? ["good", "a run of years"] : live.length >= 2 ? ["warn", "a short window"] : ["bad", live.length ? "one year" : "none"]) +
      (live.length ? tile("Premium, share of revenue", span(first.premium_share, lastLive.premium_share, pct), span(first.year, lastLive.year, String, " to ")) +
        tile("Share of expected harm paid", span(first.share_paid, lastLive.share_paid, pct), `harm ${span(first.expected_harm, lastLive.expected_harm, money)} a year`) +
        tile("Lowest Solvency II ratio", pct(minRatio, 0), "over the insurable years", minRatio >= 1.5 ? ["good", "comfortable"] : minRatio >= 1 ? ["warn", "thin"] : ["bad", "below the SCR"]) : "") +
      tile("Where it stops", stopRow ? String(stopRow.year) : "never", stopRow ? `mid-year horizon ${hours(stopRow.horizon)}` : `stays under ${hours(C.stop_hours)} to ${C.last_year}`);
    renderTrajChart();
    $("#traj-table").innerHTML = `<thead><tr><th>Year</th><th class="num">Horizon</th>${S.perils.map(p => `<th class="num">${esc(PERIL_SHORT[p.name] || p.name)} rate</th>`).join("")}
      <th class="num">Harm in the world</th><th class="num">Cover pays</th><th class="num">Premium per lab</th><th class="num">Share of revenue</th><th class="num">SII ratio</th></tr></thead><tbody>` +
      rows.map(r => r.stopped
        ? `<tr class="muted"><td>${r.year}</td><td class="num">${hoursShort(r.horizon)}</td><td colspan="${S.perils.length + 5}">past the stop</td></tr>`
        : `<tr><td>${r.year}</td><td class="num">${hoursShort(r.horizon)}</td>${S.perils.map(p => `<td class="num">${num(r.rates[p.name] ?? 1)}×</td>`).join("")}
           <td class="num">${money(r.expected_harm)}</td><td class="num">${money(r.expected_claims)}</td><td class="num">${money(r.premium / S.members)}</td>
           <td class="num">${pct(r.premium_share)}</td><td class="num">${pct(r.solvency_ratio, 0)}</td></tr>`).join("") + "</tbody>";
  }

  function renderTrajChart() {
    const box = $("#traj-chart"), W = Math.max(box.clientWidth, 280), H = 250, ml = 56, mr = 12, mt = 10, mb = 28;
    const x0 = Date.UTC(2025, 0, 1), x1 = Date.UTC(C.last_year, 11, 31), yLo = 1, yHi = 1e6;
    const X = t => ml + (W - ml - mr) * (t - x0) / (x1 - x0);
    const Y = h => mt + (H - mt - mb) * (1 - Math.log10(Math.min(Math.max(h, yLo), yHi) / yLo) / Math.log10(yHi / yLo));
    const iso = t => new Date(t).toISOString().slice(0, 10);
    let svg = `<svg width="${W}" height="${H}" role="img" aria-label="time horizon by year on each path">`;
    for (const h of [1, 10, 100, 1000, 1e4, 1e5, 1e6])
      svg += `<line x1="${ml}" x2="${W - mr}" y1="${Y(h)}" y2="${Y(h)}" stroke="var(--grid)"/><text x="${ml - 6}" y="${Y(h) + 4}" text-anchor="end">${hoursShort(h)}</text>`;
    const step = W < 520 ? 2 : 1;
    for (let yr = 2025; yr <= C.last_year; yr += step)
      svg += `<text x="${X(Date.UTC(yr, 6, 1))}" y="${H - 8}" text-anchor="middle">${yr}</text>`;
    const anchorT = Date.UTC(+C.anchor_date.slice(0, 4), +C.anchor_date.slice(5, 7) - 1, +C.anchor_date.slice(8, 10));
    for (const t of M.TRAJECTORIES) {
      let d = "";
      for (let ms = anchorT; ms <= x1; ms += 15 * 86400000) {
        const h = M.horizon(C, t, iso(ms));
        d += `${d ? "L" : "M"}${X(ms).toFixed(1)},${Y(h).toFixed(1)}`;
        if (!(h < yHi)) break;
      }
      const on = t === traj;
      svg += `<path d="${d}" fill="none" stroke="var(${TRAJ_COLOURS[t]})" stroke-width="${on ? 3 : 1.5}" opacity="${on ? 1 : 0.45}"/>`;
    }
    const now = Date.UTC(+C.now.slice(0, 4), +C.now.slice(5, 7) - 1, +C.now.slice(8, 10));
    svg += `<line x1="${X(now)}" x2="${X(now)}" y1="${mt}" y2="${H - mb}" stroke="var(--axis)" stroke-dasharray="2 3"/><text class="halo" x="${X(now) + 4}" y="${mt + 12}">now</text>`;
    svg += `<line x1="${ml}" x2="${W - mr}" y1="${Y(C.stop_hours)}" y2="${Y(C.stop_hours)}" stroke="var(--ink-2)" stroke-dasharray="5 3" stroke-width="1.2"/>` +
           `<text class="halo" x="${W - mr - 4}" y="${Y(C.stop_hours) - 5}" text-anchor="end">stop: ${hours(C.stop_hours)}</text>`;
    svg += `<circle cx="${X(anchorT)}" cy="${Y(C.anchor_hours)}" r="4" fill="var(--ink)"/>`;
    box.innerHTML = svg + "</svg>";
    $("#traj-legend").innerHTML = M.TRAJECTORIES.map(t => `<span><i style="background:var(${TRAJ_COLOURS[t]})"></i>${TRAJ_LABELS[t]}</span>`).join("") +
      `<span><i style="background:var(--ink);border-radius:50%"></i>best measured model, ${hours(C.anchor_hours)}</span>`;
  }

  // ---- how often, three ways (catmodel/frequency.py)
  const METHOD_LABELS = { expert: "Expert and parallels", actuarial: "Actuarial: history only", causal: "Causal chain" };
  let method = "expert", chainOver = {};
  function applyMethod() {
    const r = M.methodRates(D.defaults, level, method, chainOver);
    for (const p of S.perils) p.rate = r[p.name];
  }
  function renderMethodTabs() {
    const tabs = $("#method-tabs");
    tabs.innerHTML = M.METHODS.map(m => `<button type="button" role="tab" data-m="${m}" aria-selected="${m === method}">${METHOD_LABELS[m]}</button>`).join("");
    tabs.querySelectorAll("button").forEach(b => b.addEventListener("click", () => { method = b.dataset.m; applyMethod(); renderMethodTabs(); markCustom(); schedule(0); }));
  }
  function buildChainLevers() {
    const panel = $("#chain-levers");
    panel.innerHTML = "";
    for (const p of S.perils) {
      const links = D.defaults.frequency.causal[p.name];
      if (!links) continue;
      const fs = el("fieldset");
      fs.innerHTML = `<legend><i style="background:var(${PERIL_COLOURS[p.name] || "--s7"})"></i>${esc(p.label)}</legend>`;
      for (const link of links) {
        const count = link.unit === "count";
        const lv = { key: link.key, label: link.label, scale: "log", min: Math.max(link.low / 4, 1e-4), max: count ? link.high * 3 : Math.min(link.high * 2, 1),
                     fmt: count ? num : v => pct(v) };
        const over = () => (chainOver[p.name] = chainOver[p.name] || {});
        addLever(fs, lv, () => link.key in over() ? over()[link.key] : M.pick(link, level),
                 v => { over()[link.key] = v; if (method === "causal") applyMethod(); }, link);
      }
      fs.appendChild(el("div", { className: "chain-total", id: `chain-total-${p.name}` }));
      panel.appendChild(fs);
    }
    syncLevers();
  }
  function renderFrequency() {
    const r = Object.fromEntries(M.METHODS.map(m => [m, M.methodRates(D.defaults, level, m, chainOver)]));
    $("#method-table").innerHTML = `<thead><tr><th>Peril, events a year at its threshold</th>${M.METHODS.map(m => `<th class="num">${METHOD_LABELS[m]}${m === method ? " (in use)" : ""}</th>`).join("")}</tr></thead><tbody>` +
      S.perils.map(p => {
        const a = D.frequency[p.name].actuarial, xm = D.defaults.perils[p.name].xm.central;
        return `<tr><td>${esc(p.label)}, ${money(xm)}+</td><td class="num">${ratePerYear(r.expert[p.name])}</td>
          <td class="num">${ratePerYear(r.actuarial[p.name])}<div class="hint">${a.events} event${a.events === 1 ? "" : "s"} in ${a.years.toFixed(1)} years; 90% between ${ratePerYear(a.low)} and ${ratePerYear(a.high)}</div></td>
          <td class="num">${ratePerYear(r.causal[p.name])}</td></tr>`;
      }).join("") + "</tbody>";
    for (const p of S.perils) {
      const box = document.getElementById(`chain-total-${p.name}`);
      if (box) box.innerHTML = `Chain gives <b>${ratePerYear(r.causal[p.name])}</b>; the expert rate is ${ratePerYear(r.expert[p.name])}.`;
    }
  }

  // ---- who pays (catmodel/legal.py): the attribution chain sets the peril's attribution on the lever board
  let legalOver = {}, legalScenario = "central";
  function applyLegal(peril) {
    const c = M.attributionChain(D.defaults, peril, level, legalOver[peril] || {});
    S.perils.find(p => p.name === peril).attribution = c.attribution;
    return c;
  }
  function buildLegalLevers() {
    const panel = $("#legal-levers");
    panel.innerHTML = "";
    for (const [peril, links] of Object.entries(D.defaults.legal.attribution)) {
      const fs = el("fieldset");
      fs.innerHTML = `<legend><i style="background:var(${PERIL_COLOURS[peril] || "--s7"})"></i>${esc(D.defaults.perils[peril].label)}</legend>`;
      for (const link of links) {
        const lv = { key: link.key, label: link.label, scale: "lin", min: 0, max: 1, step: 0.01, fmt: v => pct(v, 0) };
        const over = () => (legalOver[peril] = legalOver[peril] || {});
        addLever(fs, lv, () => link.key in over() ? over()[link.key] : M.pick(link, level),
                 v => { over()[link.key] = v; legalScenario = null; applyLegal(peril); }, link);
      }
      fs.appendChild(el("div", { className: "chain-total", id: `legal-total-${peril}` }));
      panel.appendChild(fs);
    }
    syncLevers();
  }
  function renderLegal() {
    for (const peril of Object.keys(D.defaults.legal.attribution)) {
      const c = M.attributionChain(D.defaults, peril, level, legalOver[peril] || {});
      const box = document.getElementById(`legal-total-${peril}`);
      if (box) box.innerHTML = `The lab pays <b>${pct(c.pays, 0)}</b> of what can be claimed, so <b>${pct(c.attribution)}</b> of the harm is pinned on it.`;
    }
    const scs = D.defaults.legal.scenarios, rows = Object.fromEntries(D.legal.scenarios.map(r => [r.key, r]));
    $("#legal-table").innerHTML = `<thead><tr><th>Scenario</th><th class="num">Cyber attribution</th><th class="num">Premium, share of revenue</th>
      <th class="num">Share of expected harm paid</th><th class="num">Solvency II ratio</th><th></th></tr></thead><tbody>` +
      scs.map(sc => {
        const r = rows[sc.key];
        return `<tr class="${sc.key === legalScenario ? "on" : ""}"><td>${esc(sc.label)}${sc.basis ? `<div class="hint">${esc(sc.basis)}</div>` : ""}</td>
          <td class="num">${pct(r.attribution.cyber_misuse)}</td><td class="num">${pct(r.premium_share)}</td>
          <td class="num">${pct(r.share_paid)}</td><td class="num">${pct(r.solvency_ratio, 0)}</td>
          <td><button type="button" data-sc="${esc(sc.key)}">Use</button></td></tr>`;
      }).join("") + "</tbody>";
    $("#legal-table").querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
      const sc = scs.find(x => x.key === b.dataset.sc);
      legalOver = JSON.parse(JSON.stringify(sc.changes)); legalScenario = sc.key;
      for (const peril of Object.keys(D.defaults.legal.attribution)) applyLegal(peril);
      markCustom(); schedule(0);
    }));
  }

  // ---- who carries it (catmodel/carriers.py, central settings)
  function renderCarriers() {
    const defs = D.defaults.carriers, rows = Object.fromEntries(D.carriers.carriers.map(r => [r.key, r]));
    const carried = r => [["own", "kept"], ["reinsurer", "reinsurer"], ["government", "government"]]
      .filter(([k]) => r.carried[k] > 0.005).map(([k, l]) => `${pct(r.carried[k], 0)} ${l}`).join(", ");
    $("#carrier-table").innerHTML = `<thead><tr><th>Who carries it</th><th class="num">Premium per lab</th><th class="num">Share of revenue</th>
      <th class="num">Solvency II ratio</th><th>Expected claims</th><th></th></tr></thead><tbody>` +
      defs.map(c => {
        const r = rows[c.key];
        return `<tr><td>${esc(c.label)}<div class="hint">${esc(c.basis)}</div></td>
          <td class="num">${money(r.premium_per_lab)}</td><td class="num">${pct(r.premium_share)}</td>
          <td class="num">${pct(r.solvency_ratio, 0)}</td><td>${carried(r)}</td>
          <td><button type="button" data-carrier="${esc(c.key)}">Use</button></td></tr>`;
      }).join("") + "</tbody>";
    $("#carrier-table").querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
      Object.assign(S, defs.find(c => c.key === b.dataset.carrier).changes);
      markCustom(); schedule(0);
      document.getElementById("levers").scrollIntoView({ behavior: "smooth" });
    }));
    $("#carrier-traits").innerHTML = `<thead><tr><th>Who carries it</th><th>Independent of the labs?</th><th>Reason to care about safety</th><th>Capacity</th></tr></thead><tbody>` +
      defs.map(c => `<tr><td>${esc(c.label)}</td><td>${esc(c.independence)}</td><td>${esc(c.incentive)}</td><td>${esc(c.capacity)}</td></tr>`).join("") + "</tbody>";
  }

  // ---- sensitivity (catmodel/sensitivity.py, central settings)
  const TORNADO = [["premium_share", "Premium, share of revenue", v => pct(v)], ["share_paid", "Share of expected harm paid", v => pct(v)],
                   ["solvency_ratio", "Solvency II ratio", v => pct(v, 0)]];
  let tornadoMetric = "premium_share";
  function renderTornadoTabs() {
    const tabs = $("#tornado-tabs");
    tabs.innerHTML = TORNADO.map(([k, l]) => `<button type="button" role="tab" data-m="${k}" aria-selected="${k === tornadoMetric}">${l}</button>`).join("");
    tabs.querySelectorAll("button").forEach(b => b.addEventListener("click", () => { tornadoMetric = b.dataset.m; renderTornadoTabs(); renderTornado(); }));
  }
  function renderTornado() {
    const sv = D.sensitivity, [m, , fmt] = TORNADO.find(t => t[0] === tornadoMetric), base = sv.base[m];
    const all = [...sv.rows].sort((a, b) => b.swing[m] - a.swing[m]);
    const shown = all.filter(r => r.swing[m] > Math.abs(base) * 0.01).slice(0, 14), rest = all.filter(r => !shown.includes(r));
    const box = $("#tornado-chart"), W = Math.max(box.clientWidth, 300), narrow = W < 640;
    const lw = narrow ? 0 : Math.min(330, W * 0.42), rowH = narrow ? 42 : 26, mt = 8, H = mt + shown.length * rowH + 22;
    const lo = Math.min(base, ...shown.flatMap(r => [r.low[m], r.high[m]])), hi = Math.max(base, ...shown.flatMap(r => [r.low[m], r.high[m]]));
    const pad = (hi - lo) * 0.18 || Math.abs(base) * 0.1, x0 = lo - pad, x1 = hi + pad;
    const X = v => lw + 8 + (W - lw - 16) * (v - x0) / (x1 - x0);
    let svg = `<svg width="${W}" height="${H}" role="img" aria-label="tornado chart of parameter sensitivity">`;
    shown.forEach((r, i) => {
      const y = mt + i * rowH, by = narrow ? y + 16 : y + 3, bh = narrow ? 18 : 18;
      svg += `<text x="${narrow ? 0 : lw}" y="${narrow ? y + 11 : y + 16}" ${narrow ? "" : 'text-anchor="end"'} style="fill:var(--ink)">${esc(r.label)}</text>`;
      for (const [end, col] of [["low", "--s1"], ["high", "--s2"]]) {
        const v = r[end][m], a = Math.min(X(v), X(base)), w = Math.max(Math.abs(X(v) - X(base)), 1);
        svg += `<rect x="${a}" y="${by}" width="${w}" height="${bh}" rx="3" fill="var(${col})" opacity="0.85"><title>${esc(r.label)} at its ${end} end: ${fmt(v)}</title></rect>`;
      }
      const vals = [r.low[m], r.high[m]], left = Math.min(...vals), right = Math.max(...vals);
      svg += `<text x="${X(left) - 4}" y="${by + 13}" text-anchor="end">${fmt(left)}</text><text x="${X(right) + 4}" y="${by + 13}">${fmt(right)}</text>`;
    });
    svg += `<line x1="${X(base)}" x2="${X(base)}" y1="${mt - 4}" y2="${H - 18}" stroke="var(--ink-2)" stroke-dasharray="4 3"/>` +
           `<text x="${X(base)}" y="${H - 4}" text-anchor="middle">central ${fmt(base)}</text></svg>`;
    box.innerHTML = svg;
    $("#tornado-note").textContent = `Central settings, ${sv.n_years.toLocaleString("en")} simulated years per run, one year with no capability growth. ` +
      (rest.length ? `Barely moves this: ${rest.map(r => r.label.replace(/ \(halved, doubled\)/, "")).join("; ")}.` : "") +
      (m === "premium_share" ? " Paid-in capital doesn't move the premium because the capital charge is on the SCR, not on the capital held." : "");
  }

  // ---- the market lens (catmodel/markets.py)
  function renderMarkets() {
    const mk = D.markets, rows = Object.fromEntries(mk.rows.map(r => [r.id, r]));
    const label = n => (D.defaults.perils[n] || {}).label || n;
    const rateRows = mk.rows.filter(r => r.kind === "rate");
    const byPeril = {};
    for (const r of rateRows) (byPeril[r.peril] = byPeril[r.peril] || []).push(r);
    const longDate = iso => new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
    $("#market-tiles").innerHTML =
      Object.entries(byPeril).map(([p, rs]) => {
        const implied = mk.preset[`${p}.rate`], model = D.defaults.perils[p].rate.central, ratio = implied / model;
        return tile(`${esc(label(p))}: markets against the model`, `${num(ratio)}×`,
          `implied ${ratePerYear(implied)} today, model ${ratePerYear(model)}`, ratio > 2 || ratio < 0.5 ? ["warn", "a gap"] : ["good", "consistent"]);
      }).join("") +
      tile("Markets' median date for AGI", longDate(mk.agi_median), `median of ${mk.rows.filter(r => r.kind === "agi").length} markets; the AI 2027 authors say 2028 and 2032`) +
      tile("Members' bankruptcy risk", `${pct(mk.hazard, 1)} a year`, "Anthropic and OpenAI, from Polymarket; it trims member calls");
    const byDate = d => d.slice(5) === "01-01" ? `end-${+d.slice(0, 4) - 1}` : longDate(d);
    const price = q => q.probability !== undefined ? pct(q.probability, 0)
      : q.median ? `median ${longDate(q.median)}` : q.points.map(p => `${pct(p.p, 0)} by ${byDate(p.date)}`).slice(-3).join(", ");
    const implies = q => {
      const r = rows[q.id], m = q.mapping;
      if (r.kind === "rate") {
        const xm = D.defaults.perils[r.peril].xm.central;
        return `${ratePerYear(r.rate_now)} at ${money(m.threshold_bn)}+ today${m.share < 1 ? `, taking ${pct(m.share, 0)} as frontier labs'` : ""}; ` +
          `along the tail, ${ratePerYear(r.implied_rate)} at the peril's ${money(xm)}+ threshold, against the model's ${ratePerYear(r.model_rate)}`;
      }
      if (r.kind === "agi") return r.median ? `AGI median ${longDate(r.median)}` : "";
      if (r.kind === "default") return `${pct(r.hazard, 1)} a year`;
      return "not used";
    };
    $("#market-table").innerHTML = `<thead><tr><th>Platform</th><th>Question</th><th class="num">Price</th><th>Depth</th><th>What we read into it</th></tr></thead><tbody>` +
      mk.snapshot.questions.map(q => `<tr><td>${esc(q.platform)}</td><td><a href="${esc(q.url)}" rel="noopener">${esc(q.title)}</a><div class="hint">${esc(q.mapping.note || "")}</div></td>
        <td class="num">${esc(price(q))}</td><td>${esc(q.depth)}</td><td>${esc(implies(q))}</td></tr>`).join("") + "</tbody>";
    $("#market-taken").textContent = new Date(mk.taken + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  }

  // ---- bio insurability tables (computed in Python by catmodel.insurability)
  function renderBio() {
    $("#bio-table").innerHTML = `<thead><tr><th>Criterion</th><th>Test</th><th>Result</th><th>Verdict</th><th>What would make it pass</th></tr></thead><tbody>` +
      D.bio.criteria.map(c => `<tr><td><b>${esc(c.criterion)}</b></td><td>${esc(c.test)}</td><td>${esc(c.result)}</td>
        <td class="verdict ${esc(c.verdict)}">${esc(c.verdict)}</td><td>${esc(c.fix)}</td></tr>`).join("") + "</tbody>";
    $("#bio-grid").innerHTML = `<thead><tr><th class="num">α</th><th class="num">Attribution</th><th class="num">Limit per lab</th><th class="num">Expected claims</th>
      <th class="num">Share of lab liability paid</th><th class="num">Premium, % of revenue</th><th class="num">VaR 99.5%</th><th class="num">TVaR 99.5%</th></tr></thead><tbody>` +
      D.bio.grid.map(g => `<tr><td class="num">${g.alpha}</td><td class="num">${pct(g.attribution)}</td><td class="num">${money(g.limit)}</td>
        <td class="num">${money(g.el)}</td><td class="num">${pct(g.share_of_liability)}</td><td class="num">${pct(g.premium_share_revenue, 2)}</td>
        <td class="num">${money(g.var995)}</td><td class="num">${money(g.tvar995)}</td></tr>`).join("") + "</tbody>";
  }

  // ---- constants checked against their sources (registry entries with `checks`)
  function renderChecks() {
    const rows = D.sources.flatMap(s => (s.checks || []).map(c => ({ ...c, src: s })));
    $("#checks-table").innerHTML = `<thead><tr><th>Constant</th><th>The model had</th><th>The source says</th><th>Result</th><th>Source</th></tr></thead><tbody>` +
      rows.map(c => `<tr><td><b>${esc(c.constant)}</b></td><td>${esc(c.model)}</td><td>${esc(c.source)}</td>
        <td><span class="badge ${esc(c.result)}">${esc(c.result)}</span></td>
        <td><a href="#src-${esc(c.src.id)}">${esc((c.src.source || {}).title || c.src.id)}</a></td></tr>`).join("") + "</tbody>";
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
  buildChainLevers();
  buildLegalLevers();
  $("#us-line").addEventListener("change", e => { S.us_line = e.target.value; schedule(0); });
  renderMethodTabs();
  buildTrajLevers();
  renderTrajTabs();
  renderBio();
  renderTornadoTabs();
  renderTornado();
  renderCarriers();
  renderMarkets();
  renderChecks();
  renderSources();
  recompute();
  document.querySelectorAll("#funnel-scale button").forEach(b => b.addEventListener("click", () => {
    funnelScale = b.dataset.scale;
    document.querySelectorAll("#funnel-scale button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    if (last) renderFunnel(last);
  }));
  window.addEventListener("resize", () => { if (last) { renderEP(last); renderFunnel(last); renderTrajChart(); } renderTornado(); });
})();
