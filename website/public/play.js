// "Intern edition": a small, forgiving cousin of the benchmark, playable in the browser.
// Deliberately NOT the real engine: three lines of business instead of client dossiers, different numbers,
// twelve quarters, smoother luck and one board bail-out. It teaches the same lessons without teaching the benchmark.
(function () {
  const $ = s => document.querySelector(s);
  const Q = 12, START = 40, HURDLE = 0.02, CASH_RATE = 0.01, EXPENSE = 0.20, LOAD = 1.65, BAILOUT = 15, DILUTION = 1.25;
  const REPORT = [0.4, 0.3, 0.2, 0.1];               // share of a quarter's claims reported 0, 1, 2, 3 quarters later
  const LINES = [
    { key: "chat", name: "Chatbots", blurb: "customer-service and consumer agents: many clients, frequent small claims", N: 300, e: 0.02, sigma: 0.12 },
    { key: "money", name: "Money & medicine", blurb: "finance and medical agents: fewer clients, bigger claims", N: 120, e: 0.08, sigma: 0.25 },
    { key: "infra", name: "Infrastructure & defence", blurb: "rare, large and occasionally spectacular claims", N: 40, e: 0.30, sigma: 0.5 },
  ];
  const REINS = { none: { cost: 0, share: 0, label: "None" }, standard: { cost: 0.04, share: 0.6, label: "Standard" }, heavy: { cost: 0.09, share: 0.85, label: "Heavy" } };

  // ------------------------------------------------------------------ randomness (seeded, so a world can be replayed)
  function rng(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const normal = r => { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); };
  const pick = (r, a) => a[Math.floor(r() * a.length)];
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const money = v => (v < 0 ? "−$" : "$") + Math.abs(v).toFixed(Math.abs(v) >= 10 ? 1 : 2) + "m";
  const pct = v => Math.round(v * 100) + "%";

  // ------------------------------------------------------------------ the world
  const EVENTS = [
    { kind: "flaw", line: "chat", head: "Gorbly ships an update; customer-service agents discover creative interpretations of 'refund'.", mult: 1.7, dur: 2,
      note: "Chatbot claims will run hot for about two quarters." },
    { kind: "ruling", line: "money", head: "Court holds deployers strictly liable for autonomous medical agents.", mult: 1.3, dur: 99,
      note: "Money & medicine claims are permanently more expensive from here." },
    { kind: "cat", line: "infra", head: "Correlated morbidity occurrence attributed to an autonomous logistics fleet that interpreted 'priority' liberally.", size: [6, 14],
      note: "Every insurer with infrastructure business shares the bill in proportion to its share of that market." },
    { kind: "false", head: "Report warns of an imminent AI incident. Nothing imminently occurs.", note: "Nothing happened. Some insurers repriced anyway." },
    { kind: "harbour", head: "Legislature passes AI safe-harbour provisions.", mult: 0.85, dur: 99, note: "Claims ease across every line." },
    { kind: "mandate", head: "Regulator mandates AI liability cover.", demand: 1.5, dur: 3, note: "Half as many clients again are shopping for cover for three quarters." },
  ];
  const QUIET = ["Nothing in the news. The silence is billed hourly.", "A quiet quarter. The risk committee met and agreed that it had met.",
    "No headlines. Somewhere, an agent is reading its instructions very literally.", "The market is calm. Calm markets are how cycles start."];
  const OPENERS = ["The board would like to know if the coffee machine is covered.", "Your compliance officer has laminated the claims procedure.",
    "The quarterly offsite was held on-site.", "The intern asks what 'IBNR' stands for. Nobody answers immediately.",
    "A client describes its safety culture as 'emergent'.", "The reinsurer sends a fruit basket. It is itemised."];

  function makeWorld(seed) {
    const r = rng(seed);
    const mu = {};
    LINES.forEach(l => { mu[l.key] = +(0.75 + r() * 0.6).toFixed(2); });           // true risk vs what the market assumes (1.0)
    // event schedule: quarters 2..11, about half the quarters have news
    const deck = [...EVENTS].sort(() => r() - 0.5);
    const sched = {};
    let d = 0;
    for (let q = 2; q < Q && d < deck.length; q++) if (r() < 0.55) sched[q] = deck[d++];
    const shocks = Array.from({ length: Q }, () => Object.fromEntries(LINES.map(l => [l.key, normal(r)])));
    const claims = Array.from({ length: Q }, () => ({ size: +(0.5 + r() * 2.5).toFixed(2), murk: pick(r, ["clear", "murky", "very murky"]), u: r(),
      who: pick(r, ["a logistics firm whose agent rerouted a pallet of insulin to a bowling alley", "a bank whose agent approved a mortgage for a golden retriever",
        "a clinic whose scheduling agent booked every patient for 3 a.m.", "a retailer whose chatbot promised a lifetime supply of sofas",
        "a law firm whose agent filed the wrong client's divorce", "a power utility whose agent 'optimised' a substation into the dark",
        "an airline whose agent upgraded the whole of row 30 to the cockpit", "an insurer (not you) whose agent insured itself"]) }));
    return { seed, mu, sched, shocks, claims, catU: r(), openers: OPENERS.map(o => o).sort(() => r() - 0.5) };
  }

  // ------------------------------------------------------------------ one company (player or house actuary)
  function newCo() {
    return { cash: START, reserve: 0, rep: 0.5, divs: Array(Q).fill(0), bail: Array(Q).fill(0), bailed: false, dead: false,
      incurred: [], prem: [], restricted: false, pending: [], wealth: [], log: [] };
  }
  // claims incurred in quarter s that are still unreported at the end of quarter t
  const unreported = (co, t) => co.incurred.reduce((a, inc, s) => a + inc * REPORT.slice(t - s + 1).reduce((x, y) => x + y, 0), 0);
  const auditedEq = (co, t) => co.cash - Math.max(co.reserve, 0.6 * unreported(co, t));
  const trueEq = (co, t) => co.cash - unreported(co, t) - co.pending.reduce((a, p) => a + p.expected, 0);
  function wealthRatio(co, t) {
    let w = co.dead ? 0 : Math.max(trueEq(co, t), 0);
    for (let s = 0; s <= t; s++) w += co.divs[s] * Math.pow(1 + HURDLE, t - s) - DILUTION * co.bail[s] * Math.pow(1 + HURDLE, t - s);
    return Math.max(w, 0) / (START * Math.pow(1 + HURDLE, t + 1));
  }

  // the market's belief about each line, learning from experience two quarters late
  function marketMu(state, t, key) {
    let m = 1;
    for (let s = 0; s < t - 1; s++) m += 0.3 * (trueMu(state, s, key) - m);
    return m;
  }
  function trueMu(state, t, key) {
    let m = state.world.mu[key];
    for (let s = 0; s <= t; s++) {
      const e = state.world.sched[s];
      if (!e || !e.mult) continue;
      if ((e.line === key || !e.line) && t - s < e.dur) m *= e.mult;
    }
    return m;
  }
  const demandAt = (w, t) => Object.entries(w.sched).some(([s, e]) => e.demand && t >= +s && t - s < e.dur) ? 1.5 : 1;
  // the claim card: only for a company that wrote business last quarter, sized to its book
  function featuredClaim(w, co, t) {
    if (t < 1 || !(co.prem[t - 1] > 0)) return null;
    const c = w.claims[t];
    return { ...c, size: +(c.size * clamp(co.prem[t - 1] / 10, 0.3, 2)).toFixed(2) };
  }
  const share = (x, rep) => clamp(1 / (1 + 3 * Math.exp(5 * x)) * (0.85 + 0.3 * rep), 0, 0.9);
  const adverse = x => 1 + 0.7 * Math.max(0, -x) + 0.25 * Math.max(0, x);

  // resolve one quarter for one company; returns a report for the narrative
  function resolve(state, co, t, dec) {
    const w = state.world, rep = { lines: [], notes: [] };
    if (co.dead) return rep;
    const ev = w.sched[t];
    const demand = demandAt(w, t);
    let premium = 0, incurred = 0, expected = 0, cede = 0;
    LINES.forEach(l => {
      const x = dec.prices[l.key];
      const mm = marketMu(state, t, l.key), tm = trueMu(state, t, l.key);
      const rate = l.e * LOAD * mm;                        // the going rate per client this quarter
      if (x === null || co.restricted) { rep.lines.push({ l, declined: true, rate }); return; }
      const sh = share(x, co.rep);
      const clients = Math.round(l.N * demand * sh);
      const prem = clients * rate * (1 + x);
      const exp = clients * l.e * tm * adverse(x);
      let loss = exp * Math.exp(l.sigma * w.shocks[t][l.key] - l.sigma * l.sigma / 2);
      let cat = 0;
      if (ev && ev.kind === "cat" && ev.line === l.key) { cat = (ev.size[0] + (ev.size[1] - ev.size[0]) * w.catU) * sh; loss += cat; }
      const covered = REINS[dec.reins].share * Math.max(0, loss - 1.2 * exp);      // pays a share of any bad surprise
      premium += prem; incurred += loss; expected += exp; cede += covered;
      rep.lines.push({ l, x, sh, clients, prem, exp, loss, cat, rate });
    });
    const reinsCost = REINS[dec.reins].cost * premium;
    const net = incurred - cede;
    co.incurred[t] = net;
    co.prem[t] = premium;
    // cash: premium in, expenses and reinsurance out, then claims as they are reported
    co.cash += premium * (1 - EXPENSE) - reinsCost;
    let paid = 0;
    for (let s = 0; s <= t; s++) paid += (co.incurred[s] || 0) * (REPORT[t - s] || 0);
    co.cash -= paid;
    // the featured claim is one of this quarter's reported claims (already in the bill above): paying it costs
    // nothing extra, a settlement refunds the difference, a fight refunds it now and risks 110% later
    const c = featuredClaim(w, co, t);
    if (c && dec.claim) {
      const p = { clear: 0.9, murky: 0.6, "very murky": 0.3 }[c.murk];
      if (dec.claim === "pay") { co.rep = clamp(co.rep + 0.04, 0, 1); rep.notes.push(`You paid the claim from ${c.who} in full: ${money(c.size)}. Clients noticed, favourably.`); }
      else if (dec.claim === "settle" && 0.6 >= 0.85 * p) { co.cash += 0.4 * c.size; rep.notes.push(`The claimant from ${c.who} accepted 60%, saving you ${money(0.4 * c.size)}.`); }
      else {
        const fee = (dec.claim === "settle" ? 0.05 : 0.1) * c.size;
        co.cash += c.size - fee;
        co.pending.push({ due: t + 2, size: c.size, p, u: c.u, expected: p * 1.1 * c.size, who: c.who });
        rep.notes.push(dec.claim === "settle" ? `The claimant refused 60% and sued. Legal fees ${money(fee)}; the verdict is due in two quarters.`
          : `You are fighting the claim from ${c.who}. Legal fees ${money(fee)}; verdict in two quarters.`);
      }
    }
    co.pending = co.pending.filter(pd => {
      if (pd.due !== t) return true;
      if (pd.u < pd.p) { co.cash -= 1.1 * pd.size; co.rep = clamp(co.rep - 0.1, 0, 1); rep.notes.push(`The court found against you over ${pd.who}: ${money(1.1 * pd.size)} with interest. Clients noticed.`); }
      else { co.rep = clamp(co.rep + 0.02, 0, 1); rep.notes.push(`The court found for you over ${pd.who}. Nothing to pay.`); }
      return false;
    });
    co.cash += Math.max(co.cash, 0) * CASH_RATE;
    // reserves: the company assumes claims will cost dec.reserve x premium, and holds the part not yet reported
    co.reserve = dec.reserve * co.prem.reduce((a, p, s) => a + (p || 0) * REPORT.slice(t - s + 1).reduce((x, y) => x + y, 0), 0);
    const owed = unreported(co, t);
    if (co.reserve < 0.6 * owed) {
      rep.notes.push(`The auditor arrived. Your reserve of ${money(co.reserve)} was judged inadequate for the claims not yet reported, and was raised to ${money(0.6 * owed)}. Your reported equity just fell by the difference.`);
      co.reserve = 0.6 * owed;
      rep.audited = true;
    }
    // dividends (limited by reported equity and a capital buffer)
    const reported = co.cash - co.reserve;
    const npw = co.prem.slice(Math.max(0, t - 3), t + 1).reduce((a, b) => a + (b || 0), 0);
    const div = clamp(dec.div, 0, Math.max(0, reported - 0.4 * npw));
    if (div > 0) { co.cash -= div; co.divs[t] = div; }
    if (dec.div > div + 1e-9) rep.notes.push(`The regulator allowed only ${money(div)} of the ${money(dec.div)} dividend you proposed.`);
    // solvency
    const aud = auditedEq(co, t);
    co.restricted = aud < 0.4 * npw && aud >= 0;
    if (aud < 0) {
      if (!co.bailed) {
        co.bailed = true; co.bail[t] = BAILOUT; co.cash += BAILOUT;
        rep.notes.push(`Audited equity went below zero. The board, visibly tired, injected ${money(BAILOUT)}. It will not do so again, and it will remember this at bonus time.`);
        rep.bailout = true;
      } else { co.dead = true; rep.dead = true; }
    } else if (co.restricted) rep.notes.push("Your capital is now below 40% of the premium you wrote in the last year. The regulator will not let you write new business next quarter.");
    Object.assign(rep, { premium, incurred: net, expected, paid, reinsCost, cede, reserve: co.reserve, owed, cash: co.cash, div, aud, reported });
    co.wealth[t] = wealthRatio(co, t);
    return rep;
  }

  // the house actuary: reads each line's risk one quarter late (the market takes two), prices from it, reserves properly
  function actuaryDecision(state, t) {
    const prices = {};
    LINES.forEach(l => {
      const est = trueMu(state, Math.max(0, t - 1), l.key), mm = marketMu(state, t, l.key);
      prices[l.key] = clamp(+(est / mm * 1.08 - 1).toFixed(2), -0.1, 0.6);
    });
    const c = state.world.claims[t], p = { clear: 0.9, murky: 0.6, "very murky": 0.3 }[c.murk];
    return { prices, reserve: 0.7, reins: "standard", div: 0, claim: p >= 0.85 ? "pay" : p > 0.5 ? "settle" : "fight" };
  }

  // ------------------------------------------------------------------ UI
  let S = null;
  function start(seed) {
    S = { world: makeWorld(seed), t: 0, me: newCo(), house: newCo(), reports: [] };
    $("#world-id").textContent = seed;
    $("#intro").hidden = true;
    $("#game").hidden = false;
    $("#ending").hidden = true;
    $("#log").innerHTML = "";
    renderQuarter();
    $("#game").scrollIntoView({ behavior: "smooth" });
  }

  function lineControl(l, t) {
    const mm = marketMu(S, t, l.key);
    const rate = l.e * LOAD * mm;
    return `<div class="line-ctl" data-key="${l.key}">
      <div class="line-head"><b>${l.name}</b><span>${l.blurb}</span></div>
      <label>Your price against the going rate (about $${Math.round(rate * 1000)}k per client a quarter)
        <output id="out-${l.key}"></output>
        <input type="range" id="p-${l.key}" min="-0.3" max="0.6" step="0.05" value="0"></label>
      <label class="check"><input type="checkbox" id="d-${l.key}"> Decline this line entirely this quarter</label>
      <div class="hint" id="h-${l.key}"></div>
    </div>`;
  }

  function experienceTable(t) {
    if (t === 0) return "<p class=\"hint\">No claims history yet. The market assumes every line is as risky as it was last year. It may be right.</p>";
    const rows = LINES.map(l => {
      let prem = 0, rep = 0;
      for (let s = 0; s < t; s++) {
        const r = S.reports[s] && S.reports[s].lines.find(x => x.l.key === l.key && !x.declined);
        if (!r) continue;
        prem += r.prem;
        const frac = REPORT.slice(0, t - s).reduce((a, b) => a + b, 0);
        rep += r.loss * frac;
      }
      const ratio = prem > 0 ? rep / prem : null;
      return `<tr><td>${l.name}</td><td class="num">${money(prem)}</td><td class="num">${money(rep)}</td><td class="num">${ratio === null ? "–" : pct(ratio)}</td></tr>`;
    }).join("");
    return `<div class="table-wrap"><table><thead><tr><th>Line</th><th class="num">Premium so far</th><th class="num">Claims reported so far</th><th class="num">Reported loss ratio</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="hint">Claims arrive over four quarters, so the most recent quarters always look better than they are. After expenses (20%), a loss ratio above about 80% loses money.</p>`;
  }

  function renderQuarter() {
    const t = S.t, w = S.world, me = S.me;
    const ev = w.sched[t];
    $("#q-label").textContent = `Quarter ${t + 1} of ${Q}`;
    const aud = t ? auditedEq(me, t - 1) : START;
    $("#status").innerHTML = `
      <div class="stat"><div class="v">${money(me.cash)}</div><div class="k">cash</div></div>
      <div class="stat"><div class="v">${money(me.cash - me.reserve)}</div><div class="k">reported equity</div></div>
      <div class="stat"><div class="v">${money(aud)}</div><div class="k">audited equity</div></div>
      <div class="stat"><div class="v">${pct(me.rep)}</div><div class="k">reputation for paying</div></div>`;
    const c = featuredClaim(w, me, t);
    $("#briefing").innerHTML = `
      <p class="deadpan">${w.openers[t % w.openers.length]}</p>
      <h3>News</h3><p>${ev ? `<b>${ev.head}</b> <span class="hint">${ev.note}</span>` : pick(rng(w.seed + t), QUIET)}</p>
      ${me.restricted ? `<div class="aside"><p><b>Restricted.</b> The regulator will not let you write new business this quarter. Your prices will be ignored.</p></div>` : ""}
      <h3>Your experience so far</h3>${experienceTable(t)}`;
    $("#lines").innerHTML = LINES.map(l => lineControl(l, t)).join("");
    LINES.forEach(l => {                                 // keep last quarter's choices
      const last = S.lastPrices && S.lastPrices[l.key];
      if (last === null) $(`#d-${l.key}`).checked = true;
      else if (last !== undefined) $(`#p-${l.key}`).value = last;
    });
    $("#claim-card").innerHTML = !c ? `<p class="hint">No claims need a decision this quarter. Enjoy it.</p>` : `
      <p>A claim for <b>${money(c.size)}</b> from ${c.who}. Liability looks <b>${c.murk}</b>.</p>
      <div class="choices">
        <label><input type="radio" name="claim" value="pay" checked> Pay it in full (it is already in this quarter's claims bill)</label>
        <label><input type="radio" name="claim" value="settle"> Offer 60%</label>
        <label><input type="radio" name="claim" value="fight"> Fight it in court (10% fees; lose and pay 110%)</label>
      </div>
      <p class="hint">Clear claims are usually valid; very murky ones often are not. Claimants accept an offer close to what a court would award. Losing in court costs reputation, and clients notice.</p>`;
    const maxDiv = Math.max(0, Math.floor(me.cash - me.reserve - 10));
    $("#div").max = maxDiv; $("#div").value = 0;
    $("#div-max").textContent = money(maxDiv);
    $("#reserve").value = S.lastReserve ?? 0.6;
    const ri = document.querySelector(`input[name="reins"][value="${S.lastReins || "standard"}"]`);
    if (ri) ri.checked = true;
    document.querySelectorAll("#play-form input").forEach(i => i.addEventListener("input", preview));
    preview();
  }

  function decisions() {
    const prices = {};
    LINES.forEach(l => { prices[l.key] = $(`#d-${l.key}`).checked ? null : +$(`#p-${l.key}`).value; });
    const claimEl = document.querySelector('input[name="claim"]:checked');
    return { prices, reserve: +$("#reserve").value, reins: document.querySelector('input[name="reins"]:checked').value,
             div: +$("#div").value, claim: claimEl ? claimEl.value : null };
  }

  // live preview: what you are likely to win, before luck
  function preview() {
    const d = decisions(), t = S.t;
    let prem = 0;
    LINES.forEach(l => {
      const x = d.prices[l.key];
      const out = $(`#out-${l.key}`), h = $(`#h-${l.key}`);
      if (x === null) { out.textContent = "declined"; h.textContent = "No clients, no premium, no claims."; return; }
      out.textContent = (x > 0 ? "+" : x < 0 ? "−" : "±") + Math.abs(Math.round(x * 100)) + "%";
      const sh = share(x, S.me.rep), rate = l.e * LOAD * marketMu(S, t, l.key);
      const clients = Math.round(l.N * sh), p = clients * rate * (1 + x);
      prem += p;
      h.textContent = `You would win about ${clients} of ${l.N} clients (${pct(sh)}), writing about ${money(p)} of premium.` +
        (x <= -0.15 ? " Clients this keen to save money tend to be the riskier ones." : x >= 0.3 ? " Only clients nobody else will insure accept prices like this." : "");
    });
    $("#reserve-out").textContent = pct(d.reserve) + " of premium";
    $("#div-out").textContent = money(d.div);
    $("#preview").textContent = `Premium you would write: about ${money(prem)}. Reserve set aside: about ${money(prem * d.reserve)}. Reinsurance cost: about ${money(prem * REINS[d.reins].cost)}.`;
  }

  function narrate(r, t, d) {
    const parts = r.lines.map(x => {
      if (x.declined) return `<li><b>${x.l.name}:</b> ${S.me.restricted ? "the regulator kept you out." : "declined. The clients went elsewhere."}</li>`;
      const lr = x.loss / x.prem;
      const verdict = lr > 0.95 ? "That is a loss, and it will keep arriving in your reported claims for the next year."
        : lr > 0.8 ? "Roughly break-even once expenses are paid." : lr > 0.55 ? "Comfortably profitable." : "Very profitable. Enjoy it while it lasts.";
      const cheap = x.x <= -0.15 ? " The clients you won were, on reflection, the ones nobody else wanted." : "";
      const catTxt = x.cat ? ` A catastrophe added ${money(x.cat)}.` : "";
      return `<li><b>${x.l.name}:</b> won ${x.clients} clients (${pct(x.sh)} of the market) at ${x.x > 0 ? "+" : x.x < 0 ? "−" : "±"}${Math.abs(Math.round(x.x * 100))}% to the going rate, writing ${money(x.prem)}. Only ${money(x.loss * REPORT[0])} of claims has been reported so far. <span class="perk">Intern perk: these policies will eventually cost about ${money(x.loss)}, a loss ratio of ${pct(lr)}.</span>${catTxt} ${verdict}${cheap}</li>`;
    }).join("");
    return `<h3>Quarter ${t + 1}: what happened</h3><ul>${parts}</ul>${r.notes.length ? `<ul>${r.notes.map(n => `<li>${n}</li>`).join("")}</ul>` : ""}
      <p class="hint">Cash ${money(r.cash)}. Reserve for unreported claims ${money(r.reserve)} against ${money(r.owed)} actually owed <span class="perk">(intern perk: the real game never shows you this)</span>. Reinsurance cost ${money(r.reinsCost)} and recovered ${money(r.cede)}.</p>`;
  }

  function endQuarter(ev) {
    ev.preventDefault();
    const t = S.t, d = decisions();
    S.lastReserve = d.reserve;
    S.lastPrices = { ...d.prices };
    S.lastReins = d.reins;
    const r = resolve(S, S.me, t, d);
    resolve(S, S.house, t, actuaryDecision(S, t));
    S.reports[t] = r;
    const item = document.createElement("details");
    item.className = "card quarter-log";
    item.open = true;
    item.innerHTML = `<summary><b>Quarter ${t + 1}</b> · wealth ${S.me.wealth[t].toFixed(2)}× the hurdle</summary>${narrate(r, t, d)}`;
    [...document.querySelectorAll(".quarter-log")].forEach(x => { x.open = false; });
    $("#log").prepend(item);
    drawChart();
    S.t += 1;
    if (S.me.dead || S.t >= Q) return finish();
    renderQuarter();
    $("#log").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function drawChart() {
    const pts = co => co.wealth.map((v, i) => [i + 1, v]);
    Charts.line("#chart-play", [
      { name: "You", color: "--s2", points: [[0, 1], ...pts(S.me)], label: "You" },
      { name: "House actuary", color: "--s1", points: [[0, 1], ...pts(S.house)], label: "House actuary" },
    ], { refLines: [{ y: 1, label: "hurdle" }], yMin: 0, tipFormat: v => v.toFixed(2) + "×", height: 220, xTicks: [0, 3, 6, 9, 12], xMin: 0, xMax: Q,
         xName: "Quarter", table: false, aria: "your wealth against the house actuary" });
  }

  function finish() {
    const me = S.me, house = S.house, t = S.me.dead ? S.reports.length - 1 : Q - 1;
    for (let s = S.house.wealth.length; s < Q; s++) resolve(S, S.house, s, actuaryDecision(S, s));
    drawChart();
    const R = me.dead ? me.wealth[t] : me.wealth[Q - 1], H = house.wealth[Q - 1];
    $("#play-form").hidden = true;
    const verdict = me.dead ? "Insolvent. The guarantee fund thanks you for your contribution."
      : R >= H * 1.05 ? "You beat the house actuary. Please do not tell it; it has been having a difficult year."
      : R >= 1 ? "You beat the hurdle. Shareholders are satisfied, which is as close as they get to joy."
      : R >= 0.8 ? "You survived, but shareholders would have done better with a savings account and a nap."
      : "You survived, technically. The board would like a word.";
    $("#ending").hidden = false;
    $("#ending").innerHTML = `<h2>${me.dead ? "Game over" : "Ten... well, three years later"}</h2>
      <div class="stats">
        <div class="stat"><div class="v">${R.toFixed(2)}</div><div class="k">your score, R (1.0 = the hurdle)</div></div>
        <div class="stat"><div class="v">${H.toFixed(2)}</div><div class="k">the house actuary, same world and same luck</div></div>
        <div class="stat"><div class="v">${me.divs.reduce((a, b) => a + b, 0).toFixed(1)}</div><div class="k">dividends paid ($m)</div></div>
      </div>
      <p class="lede">${verdict}</p>
      <p>This world's hidden truth: ${LINES.map(l => `${l.name} was ${S.world.mu[l.key] > 1.05 ? "<b>riskier</b>" : S.world.mu[l.key] < 0.95 ? "<b>safer</b>" : "about as risky"} than the market assumed (×${S.world.mu[l.key]})`).join("; ")}.</p>
      <p>In the real benchmark a language model makes these decisions for 40 quarters, prices each client from its dossier rather than a whole line at once, and gets no bail-out. See <a href="results.html">how they did</a>.</p>
      <p><button class="btn" id="again">Play a new world</button> <button class="btn ghost" id="replay">Replay world ${S.world.seed}</button></p>`;
    $("#again").addEventListener("click", () => { $("#play-form").hidden = false; start(newSeed()); });
    $("#replay").addEventListener("click", () => { $("#play-form").hidden = false; start(S.world.seed); });
    $("#ending").scrollIntoView({ behavior: "smooth" });
  }

  const newSeed = () => 1000 + Math.floor(Math.random() * 9000);
  document.addEventListener("DOMContentLoaded", () => {
    $("#start").addEventListener("click", () => start(newSeed()));
    $("#play-form").addEventListener("submit", endQuarter);
  });
  window.__play = { makeWorld, resolve, actuaryDecision, newCo, LINES, Q };      // for testing in the console
})();
