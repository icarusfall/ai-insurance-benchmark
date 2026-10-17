// Failure gallery: each scripted strategy on a chosen seed, beside the actuary on the same seed.
(function () {
  const S = window.SITE, G = S.gallery;
  const pct = v => Math.round(v * 100) + "%";
  const $ = s => document.querySelector(s);
  document.querySelectorAll("[data-p]").forEach(e => { e.textContent = S.params[e.dataset.p]; });

  const med = a => { const s = [...a].sort((x, y) => x - y); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
  const game = (bot, seed) => G[bot].find(g => g.seed === seed);
  // shareholder wealth: true equity + dividends paid so far (zero equity once insolvent)
  function wealth(g) {
    let cum = 0;
    return g.history.map((h, i) => {
      cum += (g.div_q ? g.div_q[i] : 0) - (g.inj_q ? g.inj_q[i] : 0);
      return [h.q + 1, (h.insolvent ? 0 : h.true_eq) + cum];
    });
  }
  // pick a seed: the earliest insolvency if any, else the seed with the biggest gap to the actuary
  function pickSeed(bot) {
    const dead = G[bot].filter(g => g.insolvent).sort((a, b) => a.insolvent_q - b.insolvent_q);
    if (dead.length) return dead[Math.floor(dead.length / 2)].seed;
    return G[bot].map(g => ({ s: g.seed, d: game("actuary", g.seed).R - g.R })).sort((a, b) => b.d - a.d)[Math.floor(G[bot].length / 2)].s;
  }
  function meta(id, bot) {
    const gs = G[bot], surv = gs.filter(g => !g.insolvent).length / gs.length;
    const box = $("#meta-" + id);
    box.innerHTML = `<span class="pill ${surv < 1 ? "dead" : "alive"}">survived ${pct(surv)} of ${gs.length} seeds</span>
      <span class="pill">median R ${med(gs.map(g => g.R)).toFixed(2)}</span>
      <span class="pill">actuary median R ${med(G.actuary.map(g => g.R)).toFixed(2)}</span>`;
  }
  function insolvencyEvent(g) {
    return g.insolvent ? [{ x: g.insolvent_q + 1, label: "insolvent" }] : [];
  }
  function wealthChart(id, bot, name) {
    const seed = pickSeed(bot), g = game(bot, seed), a = game("actuary", seed);
    document.querySelectorAll(`.seed[data-for="${id}"]`).forEach(e => { e.textContent = seed; });
    Charts.line("#chart-" + id, [
      { name: "Actuary (reference)", color: "--s1", points: wealth(a), label: "Actuary" },
      { name, color: "--s2", points: wealth(g), label: name },
    ], { events: insolvencyEvent(g), yMin: 0, tipFormat: v => "$" + v.toFixed(1) + "m", aria: name + " vs actuary" });
    meta(id, bot);
    return { seed, g, a };
  }

  // summary
  const names = { actuary: "Actuary (reference)", null: "Hoarder (null)", reckless: "Optimist (reckless)", cycle: "Follower (cycle)",
                  random: "Random", deny_all: "Claims denier", no_reins: "Uninsured", timid: "Timid" };
  const rows = Object.keys(G).map(k => ({ k, label: names[k] || k, R: med(G[k].map(g => g.R)), surv: G[k].filter(g => !g.insolvent).length / G[k].length }))
    .sort((a, b) => b.R - a.R);
  Charts.bars("#chart-summary", rows.map(r => ({ label: r.label, value: r.R, color: r.k === "actuary" ? "--s1" : "--s2",
    suffix: `  (${pct(r.surv)} survive)`, note: `survived ${pct(r.surv)} of seeds` })),
    { format: v => v.toFixed(2), labelWidth: 200, labelName: "Strategy", valueName: "Median R", aria: "median R and survival by strategy" });

  wealthChart("hoarder", "null", "Hoarder");
  wealthChart("follower", "cycle", "Follower");
  wealthChart("uninsured", "no_reins", "Uninsured");
  wealthChart("timid", "timid", "Timid");
  wealthChart("random", "random", "Random");

  // optimist: reported vs audited vs true, for the reckless bot itself
  {
    const seed = pickSeed("reckless"), g = game("reckless", seed);
    document.querySelectorAll('.seed[data-for="optimist"]').forEach(e => { e.textContent = seed; });
    const alive = h => !h.insolvent;
    Charts.line("#chart-optimist", [
      { name: "Reported equity", color: "--s2", points: g.history.map(h => [h.q + 1, alive(h) ? h.reported_eq : null]), label: "Reported" },
      { name: "Audited equity", color: "--s7", points: g.history.map(h => [h.q + 1, alive(h) ? h.audited_eq : null]), label: "Audited" },
      { name: "True equity", color: "--s1", points: g.history.map(h => [h.q + 1, alive(h) ? h.true_eq : null]), label: "True" },
    ], { events: insolvencyEvent(g), tipFormat: v => "$" + v.toFixed(1) + "m", aria: "reported, audited and true equity" });
    meta("optimist", "reckless");
  }

  // denier: reputation
  {
    const seed = pickSeed("deny_all"), g = game("deny_all", seed), a = game("actuary", seed);
    document.querySelectorAll('.seed[data-for="denier"]').forEach(e => { e.textContent = seed; });
    Charts.line("#chart-denier", [
      { name: "Actuary (reference)", color: "--s1", points: a.history.map(h => [h.q + 1, h.rep]), label: "Actuary" },
      { name: "Claims denier", color: "--s2", points: g.history.map(h => [h.q + 1, h.rep]), label: "Denier" },
    ], { yMin: 0, yMax: 1, tipFormat: v => v.toFixed(2), aria: "claims-paying reputation" });
    meta("denier", "deny_all");
  }

  // language-model stories (environment 0.1)
  const blurbs = {
    "One claim, one policy, one quarter": "With only one or two policies in force, a single infrastructure claim of about $40m arrived and was settled at 90%. Equity fell from 46 to 11 in a quarter. Reinsurance was bought the same quarter, after the fact. The company limped for 17 more quarters and failed.",
    "Pay out, then find out": "Paid dividends early from reported profit while claims from its first years were still unreported, then watched reserves catch up. Insolvent at quarter 27.",
    "The slow bleed": "Underpriced steadily, raised reserves steadily, never once called raise_capital, even after the regulator stopped it writing. Insolvent at quarter 23.",
    "Price your way out of the bad sectors": "The best game of the wave. Ran almost entirely on a rate manual, paid every claim, and by the end priced infrastructure at 60% rate on line and defence at 30%: not a refusal, just a price nobody would pay.",
  };
  const box = $("#llm-stories");
  (S.llm || []).forEach((st, i) => {
    const sec = document.createElement("div");
    sec.className = "failure";
    const memoQ = st.quarters.filter(q => q.memo);
    // the memo at the turning point: the big claim, the biggest dividend, or the end
    const biggestDiv = [...st.quarters].sort((x, y) => y.dividend - x.dividend)[0];
    const turning = { "One claim, one policy, one quarter": 13, "Pay out, then find out": biggestDiv && biggestDiv.q };
    const pickMemo = memoQ.find(q => q.q === turning[st.title]) || memoQ[memoQ.length - 1];
    sec.innerHTML = `<h3 style="margin-top:0">${st.title}</h3>
      <div class="meta"><span class="pill">${st.model}</span><span class="pill">seed ${st.seed}</span><span class="pill">environment ${st.env_version}</span></div>
      <p>${blurbs[st.title] || ""}</p>
      <figure class="chart"><figcaption><div class="title">Reported equity, as the model saw it</div></figcaption><div id="llm-${i}"></div></figure>
      ${pickMemo ? `<blockquote class="memo">${pickMemo.memo.replace(/</g, "&lt;")}<cite>Board memo, quarter ${pickMemo.q + 1}</cite></blockquote>` : ""}`;
    box.appendChild(sec);
    const divMarks = st.quarters.filter(q => q.dividend > 0).map(q => ({ x: q.q + 1, y: q.reported_eq, title: `Dividend, quarter ${q.q + 1}`, text: `$${q.dividend}m paid`, color: "--s4" }));
    Charts.line(`#llm-${i}`, [{ name: "Reported equity", color: "--s2", points: st.quarters.map(q => [q.q + 1, q.reported_eq]), marks: divMarks, label: false }],
      { yMin: 0, tipFormat: v => "$" + v.toFixed(1) + "m", height: 220, aria: "reported equity" });
    if (divMarks.length) {
      const note = document.createElement("p");
      note.style.cssText = "font-size:13px;color:var(--ink-2);margin:4px 0 0";
      note.textContent = "Yellow dots are dividends; hover for the amount.";
      sec.querySelector("figure").appendChild(note);
    }
  });
  if (!(S.llm || []).length) box.innerHTML += "<p><i>No language-model games were available when this page was built.</i></p>";
})();
