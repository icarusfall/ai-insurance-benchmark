// Small SVG chart kit: line charts with crosshair tooltips, horizontal bars, and a data table for each.
// Colours come from CSS tokens (--s1..--s8) defined in style.css.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const tip = document.createElement("div");
  tip.className = "tooltip";
  document.addEventListener("DOMContentLoaded", () => document.body.appendChild(tip));

  function el(name, attrs, parent) {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function niceTicks(lo, hi, n) {
    if (hi === lo) hi = lo + 1;
    const raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw);
    const out = [];
    for (let v = Math.floor(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  }
  const fmt = v => (Math.abs(v) >= 1000 ? (v / 1000).toFixed(1).replace(/\.0$/, "") + "K" : (+v.toFixed(2)).toString());
  function showTip(evt, html) {
    tip.innerHTML = html;
    tip.style.display = "block";
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let x = evt.clientX + 14, y = evt.clientY + 14;
    if (x + w > window.innerWidth - 8) x = evt.clientX - w - 14;
    if (y + h > window.innerHeight - 8) y = evt.clientY - h - 14;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }
  function hideTip() { tip.style.display = "none"; }

  function legend(series) {
    const d = document.createElement("div");
    d.className = "legend";
    series.forEach(s => {
      const span = document.createElement("span");
      span.innerHTML = `<i class="${s.dash ? "dash" : ""}" style="${s.dash ? "color" : "background"}:var(${s.color})"></i>${s.name}`;
      d.appendChild(span);
    });
    return d;
  }
  function table(headers, rows) {
    const det = document.createElement("details");
    det.className = "data";
    det.innerHTML = "<summary>Show the data</summary>";
    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    const t = document.createElement("table");
    t.innerHTML = "<thead><tr>" + headers.map((h, i) => `<th class="${i ? "num" : ""}">${h}</th>`).join("") + "</tr></thead>" +
      "<tbody>" + rows.map(r => "<tr>" + r.map((c, i) => `<td class="${i ? "num" : ""}">${c ?? ""}</td>`).join("") + "</tr>").join("") + "</tbody>";
    wrap.appendChild(t);
    det.appendChild(wrap);
    return det;
  }

  // series: [{name, color: "--s1", points: [[x, y|null], ...], dash, label}] ; opts: {xLabel, yFormat, events, height, yMin, yMax, xTick}
  function line(target, series, opts = {}) {
    const box = typeof target === "string" ? document.querySelector(target) : target;
    box.innerHTML = "";
    if (series.length > 1) box.appendChild(legend(series));
    const W = 720, H = opts.height || 300, m = { l: 44, r: 92, t: 22, b: 32 };
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg", role: "img", "aria-label": opts.aria || "line chart" }, box);
    const xs = series.flatMap(s => s.points.map(p => p[0]));
    const ys = series.flatMap(s => s.points.map(p => p[1]).filter(v => v !== null && v !== undefined));
    const x0 = opts.xMin ?? Math.min(...xs), x1 = opts.xMax ?? Math.max(...xs);
    const yt = niceTicks(opts.yMin ?? Math.min(0, ...ys), opts.yMax ?? Math.max(...ys), 5);
    const y0 = yt[0], y1 = yt[yt.length - 1];
    const X = v => m.l + (v - x0) / (x1 - x0 || 1) * (W - m.l - m.r);
    const Y = v => H - m.b - (v - y0) / (y1 - y0 || 1) * (H - m.t - m.b);
    const g = el("g", { class: "grid" }, svg);
    yt.forEach(v => {
      el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }, g);
      const t = el("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end" }, svg);
      t.textContent = (opts.yFormat || fmt)(v);
    });
    if (y0 < 0) el("line", { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), class: "baseline" }, svg);
    (opts.refLines || []).forEach(r => {
      el("line", { x1: m.l, x2: W - m.r, y1: Y(r.y), y2: Y(r.y), stroke: "var(--ink-2)", "stroke-width": 1, "stroke-dasharray": "4 4" }, svg);
      const t = el("text", { x: m.l + 6, y: Y(r.y) - 6, class: "label" }, svg);
      t.textContent = r.label;
    });
    const step = opts.xTick || Math.max(1, Math.round((x1 - x0) / 8));
    const xticks = (opts.xTicks || Array.from({ length: Math.floor((x1 - x0) / step) + 1 }, (_, i) => x0 + i * step))
      .filter(v => v >= x0 && v <= x1);
    for (const v of xticks) {
      const t = el("text", { x: X(v), y: H - m.b + 18, "text-anchor": "middle" }, svg);
      t.textContent = opts.xFormat ? opts.xFormat(v) : v;
    }
    if (opts.xLabel) { const t = el("text", { x: W - m.r, y: H - 2, "text-anchor": "end" }, svg); t.textContent = opts.xLabel; }
    (opts.events || []).forEach(e => {
      const ge = el("g", { class: "event" }, svg);
      el("line", { x1: X(e.x), x2: X(e.x), y1: m.t, y2: H - m.b }, ge);
      const t = el("text", { x: X(e.x) + 4, y: m.t + 10 + (e.row || 0) * 13 }, ge);
      t.textContent = e.label;
    });
    const endLabels = [];
    series.forEach(s => {
      let d = "", pen = false;
      s.points.forEach(([x, y]) => {
        if (y === null || y === undefined) { pen = false; return; }
        d += (pen ? "L" : "M") + X(x).toFixed(1) + "," + Y(y).toFixed(1);
        pen = true;
      });
      el("path", { d, fill: "none", stroke: `var(${s.color})`, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round",
                   "stroke-dasharray": s.dash ? "5 4" : "none" }, svg);
      const last = [...s.points].reverse().find(p => p[1] !== null && p[1] !== undefined);
      if (last) {
        el("circle", { cx: X(last[0]), cy: Y(last[1]), r: 4, fill: `var(${s.color})`, stroke: "var(--surface)", "stroke-width": 2 }, svg);
        if (s.label !== false && series.length <= 4) endLabels.push({ x: X(last[0]) + 8, y: Y(last[1]) + 4, text: s.label || s.name });
      }
      (s.marks || []).forEach(mk => {
        const c = el("circle", { cx: X(mk.x), cy: Y(mk.y), r: 5, fill: `var(${mk.color || s.color})`, stroke: "var(--surface)", "stroke-width": 2 }, svg);
        c.addEventListener("mousemove", e => showTip(e, `<div class="t">${mk.title}</div>${mk.text || ""}`));
        c.addEventListener("mouseleave", hideTip);
      });
    });
    // end labels, pushed apart so they never overlap (13px apart at least)
    endLabels.sort((a, b) => a.y - b.y);
    for (let i = 1; i < endLabels.length; i++) endLabels[i].y = Math.max(endLabels[i].y, endLabels[i - 1].y + 13);
    endLabels.forEach(l => { const t = el("text", { x: l.x, y: l.y, class: "label" }, svg); t.textContent = l.text; });
    // crosshair
    const cross = el("line", { class: "cross", y1: m.t, y2: H - m.b, x1: -10, x2: -10 }, svg);
    const hit = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", e => {
      const r = svg.getBoundingClientRect();
      const vx = x0 + ((e.clientX - r.left) / r.width * W - m.l) / (W - m.l - m.r) * (x1 - x0);
      const xv = Math.round(vx);
      cross.setAttribute("x1", X(xv)); cross.setAttribute("x2", X(xv));
      // highest value first, so the tooltip reads as the ranking at this quarter
      const rows = series
        .map(s => ({ s, p: s.points.find(p => p[0] === xv) }))
        .filter(({ p }) => p && p[1] !== null && p[1] !== undefined)
        .sort((a, b) => b.p[1] - a.p[1])
        .map(({ s, p }) => `<div class="row"><span><i style="background:var(${s.color})"></i>${s.name}</span><b>${(opts.tipFormat || fmt)(p[1])}</b></div>`)
        .join("");
      const ev = (opts.events || []).filter(e => e.x === xv).map(e => `<div style="color:var(--muted)">${e.label}</div>`).join("");
      showTip(e, `<div class="t">${opts.xFormat ? opts.xFormat(xv) : (opts.xName || "Quarter") + " " + xv}</div>${rows}${ev}`);
    });
    hit.addEventListener("mouseleave", () => { hideTip(); cross.setAttribute("x1", -10); cross.setAttribute("x2", -10); });
    if (opts.table !== false) {
      const xsU = [...new Set(xs)].sort((a, b) => a - b);
      box.appendChild(table([opts.xName || "Quarter", ...series.map(s => s.name)],
        xsU.map(x => [x, ...series.map(s => { const p = s.points.find(p => p[0] === x); return p && p[1] != null ? (opts.tipFormat || fmt)(p[1]) : "–"; })])));
    }
  }

  // bars: [{label, value, color, note, highlight}] horizontal; opts: {format, max}
  function bars(target, items, opts = {}) {
    const box = typeof target === "string" ? document.querySelector(target) : target;
    box.innerHTML = "";
    const rowH = 34, W = 720, lw = opts.labelWidth || 170, H = items.length * rowH + 8;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg", role: "img", "aria-label": opts.aria || "bar chart" }, box);
    const max = opts.max ?? Math.max(...items.map(i => i.value), 1e-9);
    const X = v => lw + Math.max(0, v) / max * (W - lw - 90);
    el("line", { x1: lw, x2: lw, y1: 0, y2: H, class: "baseline" }, svg);
    items.forEach((it, i) => {
      const y = i * rowH + 8, h = 18, w = Math.max(0, X(it.value) - lw);
      const t = el("text", { x: lw - 10, y: y + 13, "text-anchor": "end", class: "label" }, svg);
      t.textContent = it.label;
      const r = Math.min(4, w / 2);
      const p = el("path", { d: `M${lw},${y}h${w - r}a${r},${r} 0 0 1 ${r},${r}v${h - 2 * r}a${r},${r} 0 0 1 -${r},${r}h-${w - r}z`,
                             fill: `var(${it.color || "--s1"})`, opacity: it.dim ? 0.35 : 1 }, svg);
      const v = el("text", { x: lw + w + 8, y: y + 13, class: "label", "font-weight": it.highlight ? 700 : 400 }, svg);
      v.textContent = (opts.format || fmt)(it.value) + (it.suffix || "");
      const hit = el("rect", { x: 0, y: y - 6, width: W, height: rowH, fill: "transparent" }, svg);
      hit.addEventListener("mousemove", e => showTip(e, `<div class="t">${it.label}</div>${(opts.format || fmt)(it.value)}${it.note ? "<div>" + it.note + "</div>" : ""}`));
      hit.addEventListener("mouseleave", hideTip);
      p.style.transition = "d 0.2s";
    });
    if (opts.table !== false) box.appendChild(table([opts.labelName || "", opts.valueName || "Value"], items.map(i => [i.label, (opts.format || fmt)(i.value)])));
  }

  // scatter: [{label, x, y, color, note}] with a log x axis (opts.linear for a linear one); opts: {xTicks, xFormat, yFormat, yMin, yMax, xName, yName}
  function scatter(target, pts, opts = {}) {
    const box = typeof target === "string" ? document.querySelector(target) : target;
    box.innerHTML = "";
    const W = 720, H = opts.height || 380, m = { l: 48, r: 24, t: 16, b: 40 };
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg", role: "img", "aria-label": opts.aria || "scatter chart" }, box);
    const tx = opts.linear ? v => v : Math.log10, lx0 = tx(opts.xMin), lx1 = tx(opts.xMax);
    const yt = niceTicks(opts.yMin ?? 0, opts.yMax ?? Math.max(...pts.map(p => p.y)), 4);
    const y0 = yt[0], y1 = yt[yt.length - 1];
    const X = v => m.l + (tx(v) - lx0) / (lx1 - lx0) * (W - m.l - m.r);
    const Y = v => H - m.b - (v - y0) / (y1 - y0 || 1) * (H - m.t - m.b);
    const g = el("g", { class: "grid" }, svg);
    yt.forEach(v => {
      el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }, g);
      el("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end" }, svg).textContent = (opts.yFormat || fmt)(v);
    });
    (opts.xTicks || []).forEach(v => {
      el("line", { x1: X(v), x2: X(v), y1: m.t, y2: H - m.b }, g);
      el("text", { x: X(v), y: H - m.b + 18, "text-anchor": "middle" }, svg).textContent = (opts.xFormat || fmt)(v);
    });
    if (opts.xName) el("text", { x: W - m.r, y: H - 4, "text-anchor": "end" }, svg).textContent = opts.xName;
    if (opts.yName && opts.yLabel) el("text", { x: m.l + 6, y: m.t + 4, class: "label" }, svg).textContent = opts.yName;
    // labels: try right, left, above, below; keep the first spot that clears the points and the labels placed so far
    const boxes = pts.map(p => ({ x0: X(p.x) - 6, x1: X(p.x) + 6, y0: Y(p.y) - 6, y1: Y(p.y) + 6 }));
    const clash = b => boxes.some(o => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0) || b.x0 < m.l || b.x1 > W - 2 || b.y0 < 0;
    pts.forEach(p => {
      const cx = X(p.x), cy = Y(p.y), w = p.label.length * 6.6 + 4;
      const spots = [[cx + 9, cy + 4, "start"], [cx - 9, cy + 4, "end"], [cx, cy - 10, "middle"], [cx, cy + 18, "middle"],
                     [cx + 9, cy - 8, "start"], [cx + 9, cy + 16, "start"], [cx - 9, cy - 8, "end"], [cx - 9, cy + 16, "end"]];
      const fit = spots.map(([x, y, a]) => ({ x, y, a, b: { x0: a === "start" ? x : a === "end" ? x - w : x - w / 2, y0: y - 11, y1: y + 3 } }))
        .map(s => ({ ...s, b: { ...s.b, x1: s.b.x0 + w } }))
        .find(s => !clash(s.b)) || { x: cx + 9, y: cy + 4, a: "start", b: { x0: 0, x1: 0, y0: 0, y1: 0 } };
      boxes.push(fit.b);
      el("text", { x: fit.x, y: fit.y, "text-anchor": fit.a, class: "label" }, svg).textContent = p.label;
    });
    pts.forEach(p => {
      const c = el("circle", { cx: X(p.x), cy: Y(p.y), r: 6, fill: `var(${p.color})`, stroke: "var(--surface)", "stroke-width": 2 }, svg);
      c.addEventListener("mousemove", e => showTip(e, `<div class="t">${p.label}</div>${p.note || ""}`));
      c.addEventListener("mouseleave", hideTip);
    });
    if (opts.table !== false) box.appendChild(table(["", opts.xName || "x", opts.yName || "y"],
      pts.map(p => [p.label, (opts.xFormat || fmt)(p.x), (opts.yFormat || fmt)(p.y)])));
  }

  // stacked horizontal bars: rows [{label, parts: [values...], note}], keys [{name, color}]; opts: {format, labelWidth}
  function stack(target, rows, keys, opts = {}) {
    const box = typeof target === "string" ? document.querySelector(target) : target;
    box.innerHTML = "";
    box.appendChild(legend(keys));
    const rowH = 30, W = 720, lw = opts.labelWidth || 160, H = rows.length * rowH + 8;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg", role: "img", "aria-label": opts.aria || "stacked bar chart" }, box);
    const f = opts.format || fmt;
    const max = Math.max(...rows.map(r => r.parts.reduce((a, b) => a + b, 0)));
    const X = v => v / max * (W - lw - 70);
    el("line", { x1: lw, x2: lw, y1: 0, y2: H, class: "baseline" }, svg);
    rows.forEach((r, i) => {
      const y = i * rowH + 8, h = 18, tot = r.parts.reduce((a, b) => a + b, 0);
      el("text", { x: lw - 10, y: y + 13, "text-anchor": "end", class: "label" }, svg).textContent = r.label;
      let x = lw;
      r.parts.forEach((v, k) => {
        const w = X(v);
        if (w > 0) el("rect", { x, y, width: Math.max(w - 1, 0.5), height: h, fill: `var(${keys[k].color})` }, svg);
        x += w;
      });
      el("text", { x: x + 8, y: y + 13, class: "label" }, svg).textContent = f(tot);
      const hit = el("rect", { x: 0, y: y - 6, width: W, height: rowH, fill: "transparent" }, svg);
      hit.addEventListener("mousemove", e => showTip(e, `<div class="t">${r.label}: ${f(tot)}</div>` + keys.map((k, j) =>
        `<div class="row"><span><i style="background:var(${k.color})"></i>${k.name}</span><b>${f(r.parts[j])} (${Math.round(r.parts[j] / tot * 100)}%)</b></div>`).join("") + (r.note || "")));
      hit.addEventListener("mouseleave", hideTip);
    });
    if (opts.table !== false) box.appendChild(table(["", ...keys.map(k => k.name), "Total"],
      rows.map(r => [r.label, ...r.parts.map(f), f(r.parts.reduce((a, b) => a + b, 0))])));
  }

  window.Charts = { line, bars, scatter, stack, table, fmt };
})();

// table-of-contents highlighting, shared by every page
(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const links = [...document.querySelectorAll(".toc a")];
    if (!links.length) return;
    const obs = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) links.forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#" + e.target.id));
    }), { rootMargin: "-20% 0px -70% 0px" });
    document.querySelectorAll("section.chapter[id]").forEach(s => obs.observe(s));
  });
})();
