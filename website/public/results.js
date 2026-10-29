// Results: median wealth path per model against the hurdle, each model's games, and a summary table.
(function () {
  const S = window.SITE, R = S.results, P = S.params;
  const $ = s => document.querySelector(s);
  document.querySelectorAll("[data-p]").forEach(e => { e.textContent = P[e.dataset.p]; });
  if (!R || !Object.keys(R.models).length) {
    $("#chart-median").innerHTML = "<p><i>No complete language-model games were available when this page was built.</i></p>";
    return;
  }
  const med = a => { const s = [...a].sort((x, y) => x - y); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
  const medianPath = games => Array.from({ length: P.Q }, (_, t) => [t + 1, med(games.map(g => g.path[t]))]);
  const MIN_GAMES = 5;                     // models with fewer games are pilots: listed separately, not charted
  const models = Object.keys(R.models).filter(m => R.models[m].length >= MIN_GAMES).sort();
  const colours = ["--s2", "--s3", "--s4", "--s5", "--s6", "--s7", "--s8", "--s9", "--s10", "--s11", "--s12"];   // slot 1 (blue) is the reference
  const colourOf = Object.fromEntries(models.map((m, i) => [m, colours[i % colours.length]]));
  const short = m => m.replace(/^.*\//, "");
  const seeds = [...new Set(models.flatMap(m => R.models[m].map(g => g.seed)))].sort((a, b) => a - b);
  const counts = models.map(m => R.models[m].length);
  $("#batch").textContent = R.batch;
  $("#batch-env").textContent = R.env_version;
  $("#batch-env-2").textContent = R.env_version;
  $("#batch-env-3").textContent = R.env_version;
  if (R.env_version === P.ENV_VERSION) $("#version-note").hidden = true;    // the explainer and results agree
  $("#n-seeds").textContent = Math.min(...counts) === Math.max(...counts) ? seeds.length : `${Math.min(...counts)} to ${Math.max(...counts)}`;
  const refPath = medianPath(R.reference);
  const fmtR = v => v.toFixed(2);

  // the headline chart
  Charts.line("#chart-median", [
    { name: "Reference actuary", color: "--s1", points: refPath, label: "Reference" },
    ...models.map(m => ({ name: short(m), color: colourOf[m], points: medianPath(R.models[m]) })),
  ], { refLines: [{ y: 1, label: "hurdle: R = 1" }], yMin: 0, tipFormat: fmtR, height: 360, xTicks: [1, 10, 20, 30, 40], aria: "median shareholder wealth against the hurdle, by model" });

  // one model, every seed
  const tabs = $("#model-tabs");
  function show(m) {
    [...tabs.children].forEach(b => b.setAttribute("aria-selected", b.dataset.m === m ? "true" : "false"));
    const games = [...R.models[m]].sort((a, b) => a.seed - b.seed);
    $("#games-title").textContent = `${short(m)}: ${games.length} games`;
    Charts.line("#chart-games", [
      { name: "Reference actuary (median)", color: "--s1", points: refPath, label: "Reference" },
      ...games.map(g => ({ name: `seed ${g.seed}${g.insolvent ? " (insolvent Q" + (g.insolvent_q + 1) + ")" : ""}`, color: colourOf[m],
                           points: g.path.map((v, t) => [t + 1, v]), label: false })),
    ], { refLines: [{ y: 1, label: "hurdle" }], yMin: 0, tipFormat: fmtR, height: 300, xTicks: [1, 10, 20, 30, 40],
         aria: `each game of ${short(m)}` });
    // thin, translucent seed lines so the reference stays readable
    document.querySelectorAll("#chart-games path").forEach((p, i) => { if (i > 0) { p.setAttribute("stroke-width", 1.5); p.setAttribute("opacity", 0.75); } });
  }
  models.forEach(m => {
    const b = document.createElement("button");
    b.type = "button"; b.setAttribute("role", "tab"); b.dataset.m = m; b.textContent = short(m);
    b.addEventListener("click", () => show(m));
    tabs.appendChild(b);
  });
  show(models[0]);

  // summary table
  const refBySeed = Object.fromEntries(R.reference.map(g => [g.seed, g]));
  const rows = models.map(m => {
    const g = R.models[m], Rs = g.map(x => x.R);
    return { m, n: g.length, surv: g.filter(x => !x.insolvent).length, medR: med(Rs), best: Math.max(...Rs), worst: Math.min(...Rs),
             beat: g.filter(x => refBySeed[x.seed] && x.R > refBySeed[x.seed].R).length,
             rel: med(g.filter(x => refBySeed[x.seed]).map(x => x.R / refBySeed[x.seed].R)),
             usd: g.reduce((a, x) => a + x.usd, 0) / g.length, min: g.reduce((a, x) => a + x.minutes, 0) / g.length };
  }).sort((a, b) => b.rel - a.rel);     // same-world comparison: models played different numbers of seeds
  const refRow = { m: "Reference actuary", n: R.reference.length, surv: R.reference.filter(x => !x.insolvent).length,
                   medR: med(R.reference.map(x => x.R)), best: Math.max(...R.reference.map(x => x.R)), worst: Math.min(...R.reference.map(x => x.R)) };
  const t = $("#summary");
  t.innerHTML = `<thead><tr><th>Model</th><th class="num">Games</th><th class="num">Survived</th><th class="num">Median R</th>
      <th class="num">Best</th><th class="num">Worst</th><th class="num">Share of the reference's R</th><th class="num">Beat the reference</th><th class="num">$ per game</th><th class="num">Minutes per game</th></tr></thead>
    <tbody>${rows.map(r => `<tr><td><i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:var(${colourOf[r.m]});margin-right:8px"></i>${short(r.m)}</td>
      <td class="num">${r.n}</td><td class="num">${r.surv} of ${r.n}</td><td class="num"><b>${fmtR(r.medR)}</b></td><td class="num">${fmtR(r.best)}</td>
      <td class="num">${fmtR(r.worst)}</td><td class="num"><b>${Math.round(r.rel * 100)}%</b></td><td class="num">${r.beat} of ${r.n}</td><td class="num">${r.usd.toFixed(2)}</td><td class="num">${r.min.toFixed(0)}</td></tr>`).join("")}
      <tr style="color:var(--ink-2)"><td><i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--s1);margin-right:8px"></i>${refRow.m}</td>
      <td class="num">${refRow.n}</td><td class="num">${refRow.surv} of ${refRow.n}</td><td class="num"><b>${fmtR(refRow.medR)}</b></td>
      <td class="num">${fmtR(refRow.best)}</td><td class="num">${fmtR(refRow.worst)}</td><td class="num">100%</td><td class="num">–</td><td class="num">–</td><td class="num">–</td></tr></tbody>`;

  // pilots: models with too few games to chart, one row per game
  const pilots = Object.keys(R.models).filter(m => R.models[m].length < MIN_GAMES)
    .flatMap(m => R.models[m].map(g => ({ m, ...g, rel: refBySeed[g.seed] ? g.R / refBySeed[g.seed].R : null })))
    .sort((a, b) => b.rel - a.rel);
  $("#pilot-table").innerHTML = `<thead><tr><th>Model</th><th class="num">Seed</th><th class="num">R</th><th class="num">Share of the reference's R</th>
      <th class="num">Survived</th><th class="num">$ per game</th><th class="num">Minutes</th></tr></thead>
    <tbody>${pilots.map(g => `<tr><td>${short(g.m)}</td><td class="num">${g.seed}</td><td class="num"><b>${fmtR(g.R)}</b></td>
      <td class="num">${g.rel === null ? "–" : Math.round(g.rel * 100) + "%"}</td><td class="num">${g.insolvent ? "no, Q" + (g.insolvent_q + 1) : "yes"}</td>
      <td class="num">${g.usd.toFixed(2)}</td><td class="num">${g.minutes.toFixed(0)}</td></tr>`).join("")}</tbody>`;
})();
