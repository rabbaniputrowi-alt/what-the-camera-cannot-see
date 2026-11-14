/* Page logic: loads the precomputed layers, draws the before and after viewer, and scores any date pair
   in the browser with the same code the pipeline is checked against (score.js). No external requests. */
(async function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const D = "data/";
  const meta = await (await fetch(D + "meta.json")).json();
  const N = meta.ncell, PX = meta.display_px, CELL = meta.cell_px;
  const BLOCK = 5, BN = PX / BLOCK;                  // display change layer: 5 px blocks, about 100 m
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const fmt = (d) => { const p = d.split("-"); return `${+p[2]} ${MONTHS[+p[1] - 1]} ${p[0]}`; };
  const num = (v) => v.toLocaleString("en-US");
  const pct = (v, dp) => (v === null ? "n/a" : (v * 100).toFixed(dp === undefined ? 0 : dp) + "%");
  const auc2 = (v) => (v === null ? "n/a" : v.toFixed(2));

  const state = { w: Object.keys(meta.windows)[0], tr: null, pol: "hv", a: null, b: null, seq: 0 };
  const cache = { cells: {}, labels: {}, hot: {}, opt: {}, gray: new Map() };
  let cells = null, labels = null, hot = null, optImg = null, changeCanvas = null, ch = null;

  const imgA = $("img-a"), imgB = $("img-b"), overlay = $("overlay"), ctx = overlay.getContext("2d");
  const win = () => meta.windows[state.w];
  const trk = () => win().tracks[state.tr];
  const src = (d) => `${D}img/${state.w}_t${state.tr}_${d}_${state.pol}.webp`;

  /* ---------- loading ---------- */
  async function bin(url, Type) { return new Type(await (await fetch(D + url)).arrayBuffer()); }
  function image(url) {
    return new Promise((ok, fail) => { const i = new Image(); i.onload = () => ok(i); i.onerror = fail; i.src = url; });
  }
  async function loadData() {
    const ck = state.w + "/" + state.tr;
    if (!cache.cells[ck]) cache.cells[ck] = await bin(trk().cells, Int16Array);
    if (!cache.labels[state.w]) cache.labels[state.w] = await bin(win().optical.labels, Uint8Array);
    if (!cache.hot[state.w]) cache.hot[state.w] = (await (await fetch(D + win().hotspots.file)).json()).points;
    if (!cache.opt[state.w]) cache.opt[state.w] = await image(D + win().optical.overlay);
    cells = cache.cells[ck]; labels = cache.labels[state.w]; hot = cache.hot[state.w]; optImg = cache.opt[state.w];
  }

  /* Mean grey level of each 5 px block of a displayed image, used only for the display change layer. */
  function grey(img, key) {
    if (cache.gray.has(key)) return cache.gray.get(key);
    const c = document.createElement("canvas"); c.width = PX; c.height = PX;
    const g = c.getContext("2d", { willReadFrequently: true });
    g.drawImage(img, 0, 0, PX, PX);
    const px = g.getImageData(0, 0, PX, PX).data, out = new Float32Array(BN * BN);
    for (let r = 0; r < PX; r++) {
      const br = (r / BLOCK | 0) * BN;
      for (let col = 0; col < PX; col++) out[br + (col / BLOCK | 0)] += px[(r * PX + col) * 4];
    }
    for (let k = 0; k < out.length; k++) out[k] /= BLOCK * BLOCK;
    cache.gray.set(key, out);
    return out;
  }

  function buildChange() {
    const ga = grey(imgA, src(state.a)), gb = grey(imgB, src(state.b));
    const [lo, hi] = meta.stretch_db[state.pol], k = (hi - lo) / 255;
    const c = document.createElement("canvas"); c.width = BN; c.height = BN;
    const g = c.getContext("2d"), im = g.createImageData(BN, BN), d = im.data;
    for (let i = 0; i < ga.length; i++) {
      const db = (gb[i] - ga[i]) * k, t = Math.min(1, Math.max(0, (Math.abs(db) - 0.7) / 1.8));
      if (db < 0) { d[i * 4] = 216; d[i * 4 + 1] = 30; d[i * 4 + 2] = 40; }
      else { d[i * 4] = 42; d[i * 4 + 1] = 111; d[i * 4 + 2] = 255; }
      d[i * 4 + 3] = t * 215;
    }
    g.putImageData(im, 0, 0);
    changeCanvas = c;
  }

  /* ---------- drawing ---------- */
  function draw() {
    ctx.clearRect(0, 0, PX, PX);
    if ($("layer-opt").checked && optImg) { ctx.imageSmoothingEnabled = false; ctx.drawImage(optImg, 0, 0, PX, PX); }
    if ($("layer-change").checked && changeCanvas) { ctx.imageSmoothingEnabled = true; ctx.drawImage(changeCanvas, 0, 0, PX, PX); }
    if ($("layer-rule").checked && ch) {
      const rule = Math.round(meta.rule_db * 100);
      ctx.fillStyle = "rgba(255,43,208,0.62)";
      for (let k = 0; k < ch.length; k++) if (ch[k] <= rule) ctx.fillRect((k % N) * CELL, (k / N | 0) * CELL, CELL, CELL);
    }
    let shown = 0;
    if (hot) {
      const on = $("layer-hot").checked;
      ctx.fillStyle = "rgba(255,230,0,0.8)"; ctx.strokeStyle = "rgba(0,0,0,0.55)"; ctx.lineWidth = 0.7;
      for (const p of hot) {
        if (p[2] <= state.a || p[2] > state.b) continue;
        shown++;
        if (!on) continue;
        ctx.beginPath(); ctx.arc(p[0] * PX, p[1] * PX, 3.2, 0, 6.2832); ctx.fill(); ctx.stroke();
      }
    }
    $("hot-count").textContent = num(shown);
  }

  /* ---------- scores ---------- */
  function scoreFor(a, b, pol) {
    const d = trk().dates;
    return Score.scorePair(Score.change(cells, N, d.indexOf(a), d.indexOf(b), pol, meta.cell_nodata), labels, meta.rule_db);
  }
  const isPlacebo = (a, b) => a <= meta.pre_season_end && b <= meta.pre_season_end;

  function live() {
    const j = state.pol === "hv" ? 0 : 1, s = scoreFor(state.a, state.b, j), P = state.pol.toUpperCase();
    const lead = isPlacebo(state.a, state.b)
      ? "Placebo pair: both passes are before the fire season, so nothing should show. "
      : "";
    const fire = s.flaggedBurned + s.flaggedUnburned;
    const rule = fire
      ? `Where the optical map can judge, the rule is right <b>${pct(s.precision)}</b> of the time (${num(s.flaggedBurned)} of ${num(fire)} flagged cells are burned). It fires on <b>${pct(s.falseAlarm, 1)}</b> of unburned cells and catches <b>${pct(s.recall)}</b> of burned cells.`
      : "The rule flags no cell that the optical map can judge.";
    $("live").innerHTML = `${lead}${P}, ${fmt(state.a)} to ${fmt(state.b)}: AUC <b>${auc2(s.auc)}</b> ` +
      `(the chance that a burned cell lost more echo than an unburned one; 0.50 means no signal). ` +
      `The rule "${P} fell by 1 dB or more" flags ${num(s.flagged)} of ${num(N * N)} cells. ${rule}`;
  }

  function pairList() {
    const t = trk(), pre = t.pre_season, out = [];
    for (let i = 0; i + 1 < pre.length; i++) out.push([pre[i], pre[i + 1], "placebo"]);
    for (const d of t.dates) if (d > t.baseline) out.push([t.baseline, d, "fire"]);
    return out;
  }
  function table() {
    const body = $("pairs").tBodies[0];
    body.textContent = "";
    for (const [a, b, kind] of pairList()) {
      const hv = scoreFor(a, b, 0), hh = scoreFor(a, b, 1), fire = hv.flaggedBurned + hv.flaggedUnburned;
      const tr = document.createElement("tr");
      tr.className = kind + (a === state.a && b === state.b ? " current" : "");
      const cellsOut = [kind === "placebo" ? "Placebo" : "Fire season", fmt(a), fmt(b), auc2(hv.auc), auc2(hh.auc),
        fire ? `${pct(hv.precision)} (${num(hv.flaggedBurned)} of ${num(fire)})` : "nothing flagged",
        pct(hv.falseAlarm, 1), pct(hv.recall)];
      for (const c of cellsOut) { const td = document.createElement("td"); td.textContent = c; tr.appendChild(td); }
      tr.addEventListener("click", () => { state.a = a; state.b = b; syncDates(); render(); });
      body.appendChild(tr);
    }
    const c = win().optical.counts;
    $("label-note").textContent = `${win().label}: the optical map labels ${num(+c[3] + +c[4])} cells as burned ` +
      `(${num(+c[4])} of them severe) and ${num(+c[1])} as unburned. ${num(+c[2])} cells in between are not scored, ` +
      `and ${num(+c[0])} cells have no clear optical view. Cells are about 200 m on a side.`;
  }

  /* ---------- controls ---------- */
  function seg(el, items, current, onPick) {
    el.textContent = "";
    for (const [value, text] of items) {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = text; b.setAttribute("aria-pressed", String(value === current));
      b.addEventListener("click", () => onPick(value));
      el.appendChild(b);
    }
  }
  function syncDates() {
    const d = trk().dates, A = $("date-a"), B = $("date-b");
    A.textContent = ""; B.textContent = "";
    for (const x of d.slice(0, -1)) A.add(new Option(fmt(x), x, false, x === state.a));
    if (state.b <= state.a) state.b = d[d.indexOf(state.a) + 1];
    for (const x of d) if (x > state.a) B.add(new Option(fmt(x), x, false, x === state.b));
    const later = d.filter((x) => x > state.a), i = later.indexOf(state.b);
    $("prev-b").disabled = i <= 0; $("next-b").disabled = i >= later.length - 1;
  }
  function firePair() {
    const t = trk(), late = t.dates.filter((x) => x > t.baseline && x <= "2026-10-25");
    return [t.baseline, late.length ? late[late.length - 1] : t.dates[t.dates.length - 1]];
  }
  function placeboPair() { const p = trk().pre_season; return [p[p.length - 2], p[p.length - 1]]; }

  function controls() {
    seg($("pick-window"), Object.entries(meta.windows).map(([k, v]) => [k, v.label]), state.w, async (w) => {
      state.w = w; if (!win().tracks[state.tr]) state.tr = Object.keys(win().tracks)[0];
      await enter(false);
    });
    seg($("pick-track"), Object.entries(win().tracks).map(([k, v]) => [k, `Track ${k}, ${v.direction}`]), state.tr, async (t) => {
      state.tr = t; await enter(true);
    });
    for (const b of $("pick-pol").children) b.setAttribute("aria-pressed", String(b.dataset.pol === state.pol));
  }

  /* Enter a window and track. Keeps the dates when they exist on the new track, else resets to the fire pair. */
  async function enter(resetDates) {
    await loadData();
    const d = trk().dates;
    if (resetDates || !d.includes(state.a) || !d.includes(state.b)) [state.a, state.b] = firePair();
    controls(); syncDates(); render();
  }

  async function render() {
    const seq = ++state.seq;
    $("tag-a").textContent = `Before: ${fmt(state.a)}`;
    $("tag-b").textContent = `After: ${fmt(state.b)}`;
    imgA.alt = `${state.pol.toUpperCase()} radar image, ${fmt(state.a)}`;
    imgB.alt = `${state.pol.toUpperCase()} radar image, ${fmt(state.b)}`;
    const d = trk().dates;
    ch = Score.change(cells, N, d.indexOf(state.a), d.indexOf(state.b), state.pol === "hv" ? 0 : 1, meta.cell_nodata);
    live(); table(); syncDates();
    changeCanvas = null; draw();
    imgA.src = src(state.a); imgB.src = src(state.b);
    try { await Promise.all([imgA.decode(), imgB.decode()]); } catch (e) { return; }
    if (seq !== state.seq) return;                   // a newer selection replaced this one
    buildChange(); draw();
    const later = d.filter((x) => x > state.a), i = later.indexOf(state.b);
    for (const x of [later[i - 1], later[i + 1]]) if (x) new Image().src = src(x);   // warm the neighbours
  }

  /* ---------- wiring ---------- */
  function slide() {
    const p = +$("slide").value;
    $("after").style.clipPath = `inset(0 0 0 ${p}%)`;
    $("divider").style.left = p + "%";
  }
  $("slide").addEventListener("input", slide);
  for (const id of ["layer-change", "layer-rule", "layer-hot", "layer-opt"]) $(id).addEventListener("change", draw);
  for (const b of $("pick-pol").children) b.addEventListener("click", () => { state.pol = b.dataset.pol; controls(); render(); });
  $("date-a").addEventListener("change", (e) => { state.a = e.target.value; syncDates(); render(); });
  $("date-b").addEventListener("change", (e) => { state.b = e.target.value; render(); });
  function step(k) {
    const later = trk().dates.filter((x) => x > state.a), i = later.indexOf(state.b) + k;
    if (i >= 0 && i < later.length) { state.b = later[i]; render(); }
  }
  $("prev-b").addEventListener("click", () => step(-1));
  $("next-b").addEventListener("click", () => step(1));
  $("preset-fire").addEventListener("click", () => { [state.a, state.b] = firePair(); render(); });
  $("preset-placebo").addEventListener("click", () => { [state.a, state.b] = placeboPair(); render(); });

  $("scale-note").textContent = "Each image is about 22 km across, north up. Dates are UTC. Brighter means a stronger radar echo.";
  state.tr = win().tracks["125"] ? "125" : Object.keys(win().tracks)[0];
  slide();
  await enter(true);
})();
