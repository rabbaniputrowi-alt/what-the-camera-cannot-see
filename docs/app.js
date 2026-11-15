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

  const state = { w: Object.keys(meta.windows)[0], tr: null, pol: "hv", a: null, b: null, seq: 0, mode: "camera" };
  const BLANK = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";
  const cache = { cells: {}, labels: {}, hot: {}, opt: {}, passes: {}, gray: new Map() };
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
    if (win().passes && !cache.passes[state.w]) cache.passes[state.w] = (await (await fetch(D + win().passes.file)).json());
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

  async function buildChange(seq) {
    const [ia, ib] = await Promise.all([image(src(state.a)), image(src(state.b))]);
    if (seq !== state.seq) return false;             // a newer selection replaced this one
    const ga = grey(ia, src(state.a)), gb = grey(ib, src(state.b));
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
    return true;
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
    const fire = s.flaggedBurned + s.flaggedUnburned;
    $("r-title").textContent = `${P}, ${fmt(state.a)} to ${fmt(state.b)}`;
    $("r-placebo").hidden = !isPlacebo(state.a, state.b);
    $("r-auc").textContent = auc2(s.auc);
    $("r-prec").textContent = fire ? pct(s.precision) : "none";
    $("r-fa").textContent = pct(s.falseAlarm, 1);
    $("r-rec").textContent = pct(s.recall);
    $("live").textContent = `The rule "${P} fell by 1 dB or more" flags ${num(s.flagged)} of ${num(N * N)} cells` +
      (fire ? `; ${num(s.flaggedBurned)} of the ${num(fire)} the optical map can judge are burned.` : `; none of them can be judged by the optical map.`);
  }

  /* Time series: median change since the baseline for burned and unburned cells, with hotspot counts per interval. */
  function series() {
    const t = trk(), d = t.dates, j = state.pol === "hv" ? 0 : 1, P = state.pol.toUpperCase();
    const W = 760, H = 264, L = 48, R = 14, T = 12, B = 46;
    const day = (s) => Date.parse(s + "T00:00:00Z") / 864e5, x0 = day(d[0]), x1 = day(d[d.length - 1]);
    const X = (s) => L + (day(s) - x0) / (x1 - x0) * (W - L - R);
    const pts = d.map((x) => {
      if (x === t.baseline) return [0, 0];
      const s = scoreFor(t.baseline, x, j);
      return [s.medianBurned, s.medianUnburned];
    });
    const lo = Math.floor(Math.min(-0.5, ...pts.flat()) * 2) / 2, hi = Math.ceil(Math.max(0.5, ...pts.flat()) * 2) / 2;
    const Y = (v) => T + (hi - v) / (hi - lo) * (H - T - B);
    const counts = d.map((x, i) => (i ? hot.filter((p) => p[2] > d[i - 1] && p[2] <= x).length : 0));
    const top = Math.max(1, ...counts), barH = (H - T - B) * 0.45;
    const short = (s) => { const p = s.split("-"); return `${+p[2]} ${MONTHS[+p[1] - 1]}`; };
    let g = "";
    for (let v = lo; v <= hi + 1e-9; v += 0.5) {
      g += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" style="stroke:${v === 0 ? "var(--ink-3)" : "var(--line)"}"/>` +
        `<text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v > 0 ? "+" : ""}${v.toFixed(1)}</text>`;
    }
    d.forEach((x, i) => {
      if (i && counts[i]) {
        const h = counts[i] / top * barH;
        g += `<rect x="${X(d[i - 1]) + 1}" y="${H - B - h}" width="${X(x) - X(d[i - 1]) - 2}" height="${h}" fill="#f2d200" opacity="0.2"/>` +
          `<line x1="${X(d[i - 1]) + 1}" x2="${X(x) - 1}" y1="${H - B - h}" y2="${H - B - h}" stroke="#f2d200" stroke-width="1.5"/>` +
          `<text x="${(X(x) + X(d[i - 1])) / 2}" y="${H - B - 4}" text-anchor="middle" style="fill:#f2d200">${num(counts[i])}</text>`;
      }
      g += `<text x="${X(x)}" y="${H - B + 18}" text-anchor="middle">${short(x)}</text>`;
    });
    for (const [x, name] of [[state.a, "before"], [state.b, "after"]]) {
      g += `<line x1="${X(x)}" x2="${X(x)}" y1="${T}" y2="${H - B}" style="stroke:var(--ink-2)" stroke-dasharray="4 3"/>` +
        `<text x="${X(x)}" y="${H - B + 34}" text-anchor="middle" font-weight="650" style="fill:var(--ink)">${name}</text>`;
    }
    const line = (k, colour) => `<polyline fill="none" style="stroke:${colour}" stroke-width="2.2" points="${d.map((x, i) => `${X(x)},${Y(pts[i][k])}`).join(" ")}"/>` +
      d.map((x, i) => `<circle cx="${X(x)}" cy="${Y(pts[i][k])}" r="3.4" style="fill:${colour}"/>`).join("");
    g += line(1, "var(--ink)") + line(0, "var(--red)");
    $("series").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${P} change since the baseline pass for burned and unburned cells, by date">${g}</svg>`;
    $("series-title").textContent = `${P} over the season: median change in dB since ${fmt(t.baseline)}`;
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

  /* ---------- every pass of the season: optical thumbnails and radar thumbnails, counted per period ---------- */
  const short = (s) => { const p = s.split("-"); return `${+p[2]} ${MONTHS[+p[1] - 1]}`; };
  function passPanel() {
    const info = win().passes, box = $("pass-periods");
    $("passes").hidden = !info;
    if (!info) return;
    const all = cache.passes[state.w], rule = all.rule, peak = info.periods[info.periods.length - 1];
    $("pass-lead").innerHTML = `${peak.label}, ${short(peak.from)} to ${fmt(peak.to)}: the optical satellites made <b>${peak.optical}</b> full passes over this window ` +
      `and got <b>${peak.usable}</b> usable look${peak.usable === 1 ? "" : "s"}` +
      `${peak.usable_dates.length && peak.usable <= 2 ? " (" + peak.usable_dates.map(short).join(", ") + ")" : ""}. ` +
      `The radar passed <b>${peak.radar}</b> times and returned an image on <b>${peak.radar_ok}</b> of them.`;
    $("pass-rule").textContent = `A usable look, by a rule fixed before counting: the pass covers at least ${pct(rule.min_coverage)} of the window ` +
      `and the optical product's own cloud mask calls less than ${pct(rule.max_cloud)} of it cloud. Landsat 8, Landsat 9 and Sentinel-2, ` +
      `every pass from ${fmt(all.period[0])} to ${fmt(all.period[1])}. Same-day Landsat and Sentinel-2 passes count separately. ` +
      `Bold dates with a light frame are usable looks. Faded images are passes that covered only part of the window; they are not counted. ` +
      `Nothing is masked in these images.`;
    box.textContent = "";
    for (const per of info.periods) {
      const div = document.createElement("div"); div.className = "period";
      const h = document.createElement("h3"); h.textContent = `${per.label}: ${short(per.from)} to ${fmt(per.to)}`; div.appendChild(h);
      const pc = document.createElement("p");
      pc.textContent = `Camera: ${per.usable} usable look${per.usable === 1 ? "" : "s"} in ${per.optical} full passes.`; div.appendChild(pc);
      const s1 = document.createElement("div"); s1.className = "strip";
      for (const p of all.passes) {
        if (p.date < per.from || p.date > per.to) continue;
        const el = document.createElement(p.file ? "a" : "span");
        el.className = "pass" + (p.usable ? " usable" : "") + (p.coverage < rule.min_coverage ? " partial" : "");
        const cover = p.coverage < rule.min_coverage ? `, covers ${pct(p.coverage)} of the window` : "";
        el.title = `${p.sensor}, ${fmt(p.date)}: ${p.cloud === undefined ? "no data over the window" : pct(p.cloud) + " cloud by its own mask"}${cover}`;
        if (p.file) {
          el.href = D + p.file; el.target = "_blank"; el.rel = "noopener";
          const im = document.createElement("img"); im.loading = "lazy"; im.alt = el.title; im.src = D + p.file; im.width = 74; im.height = 74;
          el.appendChild(im);
        }
        el.appendChild(document.createTextNode(short(p.date)));
        s1.appendChild(el);
      }
      div.appendChild(s1);
      const pr = document.createElement("p");
      pr.textContent = `Radar: ${per.radar_ok} image${per.radar_ok === 1 ? "" : "s"} in ${per.radar} passes. Select one to put it in the viewer.`; div.appendChild(pr);
      const s2 = document.createElement("div"); s2.className = "strip";
      for (const r of info.radar) {
        if (r.date < per.from || r.date > per.to) continue;
        const b = document.createElement("button");
        b.type = "button"; b.className = "pass usable"; b.dataset.date = r.date; b.dataset.track = r.track;
        b.title = `NISAR HV, ${fmt(r.date)}, track ${r.track}`;
        const im = document.createElement("img"); im.alt = b.title; im.src = D + r.file; im.width = 74; im.height = 74;
        b.appendChild(im); b.appendChild(document.createTextNode(short(r.date)));
        b.addEventListener("click", async () => {
          const t = win().tracks[r.track];
          state.tr = r.track; state.b = r.date;
          if (!t.dates.includes(state.a) || state.a >= r.date) state.a = r.date > t.baseline ? t.baseline : t.dates[0];
          if (state.a >= state.b) state.b = t.dates[1];
          await loadData(); controls(); syncDates(); buildTimeline(); render();
          closeAbout();
        });
        s2.appendChild(b);
      }
      div.appendChild(s2);
      box.appendChild(div);
    }
    $("pass-note").textContent = info.note;
    markPass();
  }
  function markPass() {
    for (const b of document.querySelectorAll("#pass-periods button.pass"))
      b.setAttribute("aria-pressed", String(b.dataset.date === state.b && b.dataset.track === state.tr));
  }

  /* ---------- filmstrip: one tile per radar pass of this orbit, camera image beside the radar image ---------- */
  function buildTimeline() {
    const info = win().passes, d = trk().dates, film = $("film"), cams = win().camera || {};
    const thumbs = {};
    if (info) for (const r of info.radar) if (r.track === state.tr) thumbs[r.date] = D + r.file;
    const cnt = $("t-counts"); cnt.textContent = "";
    if (info) info.periods.forEach((per, i) => {
      const el = document.createElement("span");
      if (i === info.periods.length - 1) el.className = "peak";
      el.innerHTML = `${per.label} (${short(per.from)} to ${short(per.to)}): camera <b>${per.usable}</b> usable of ${per.optical}, radar <b>${per.radar_ok}</b> of ${per.radar}`;
      cnt.appendChild(el);
    });
    film.textContent = "";
    d.forEach((date, i) => {
      const b = document.createElement("button"); b.type = "button"; b.className = "tile"; b.dataset.date = date;
      const cam = cams[date], fires = i ? hot.filter((q) => q[2] > d[i - 1] && q[2] <= date).length : 0;
      const camText = cam ? `${cam.sensor} ${short(cam.hls_date)}, ${pct(cam.cloud)} cloud by its own mask` : "no camera pass within 3 days";
      b.title = `Radar pass ${fmt(date)}. Camera: ${camText}.`;
      b.setAttribute("aria-label", b.title);
      b.innerHTML = `<span class="pics"><span class="pic">${cam ? `<img loading="lazy" alt="" src="${D + cam.file}">` : "No camera pass"}</span>` +
        `<span class="pic"><img loading="lazy" alt="" src="${thumbs[date] || `${D}img/${state.w}_t${state.tr}_${date}_hv.webp`}"></span></span>` +
        `<span class="tl"><b>${short(date)}</b><span>${i ? num(fires) + " fires" : "first pass"}</span></span>`;
      b.addEventListener("click", () => {
        stopPlay();
        if (date > state.a) state.b = date;
        else if (date === d[0]) { state.a = d[0]; state.b = d[1]; }
        else { state.a = d[0]; state.b = date; }
        syncDates(); render();
      });
      film.appendChild(b);
    });
  }
  function markTimeline() {
    const film = $("film");
    for (const b of film.children) {
      b.classList.toggle("is-a", b.dataset.date === state.a); b.classList.toggle("is-b", b.dataset.date === state.b);
      b.setAttribute("aria-pressed", String(b.dataset.date === state.b));
      if (b.dataset.date === state.b && film.scrollWidth > film.clientWidth) film.scrollLeft = b.offsetLeft - film.clientWidth / 2 + b.offsetWidth / 2;
    }
  }

  /* Play: step the after date through the season, one pass at a time. */
  let playTimer = null;
  function stopPlay() { if (playTimer) { clearInterval(playTimer); playTimer = null; } $("play").classList.remove("playing"); $("play").setAttribute("aria-label", "Play through the season"); }
  function startPlay() {
    const d = trk().dates;
    if (state.b === d[d.length - 1]) { state.a = d[0]; state.b = d[1]; syncDates(); render(); }
    $("play").classList.add("playing"); $("play").setAttribute("aria-label", "Pause");
    playTimer = setInterval(() => {
      const later = trk().dates.filter((x) => x > state.a), i = later.indexOf(state.b);
      if (i < 0 || i >= later.length - 1) { stopPlay(); return; }
      state.b = later[i + 1]; syncDates(); render();
      if (i + 1 >= later.length - 1) stopPlay();
    }, 1400);
  }
  $("play").addEventListener("click", () => (playTimer ? stopPlay() : startPlay()));

  /* About drawer */
  function openAbout(target) {
    $("about").hidden = false; $("scrim").hidden = false; $("open-about").setAttribute("aria-expanded", "true");
    if (target) $(target).scrollIntoView({ block: "start" }); else $("about").scrollTop = 0;
    $("close-about").focus();
  }
  function closeAbout() {
    if ($("about").hidden) return;
    $("about").hidden = true; $("scrim").hidden = true; $("open-about").setAttribute("aria-expanded", "false"); $("open-about").focus();
  }
  $("open-about").addEventListener("click", () => openAbout());
  $("open-scores").addEventListener("click", () => openAbout("scores"));
  $("close-about").addEventListener("click", closeAbout);
  $("scrim").addEventListener("click", closeAbout);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAbout(); });

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
    const pw = $("pick-window"); pw.textContent = "";
    for (const [k, v] of Object.entries(meta.windows)) {
      const parts = v.label.split(", "), b = document.createElement("button");
      b.type = "button"; b.setAttribute("aria-pressed", String(k === state.w)); b.setAttribute("aria-label", v.label);
      const n = document.createElement("span"); n.className = "pn"; n.textContent = parts[0].replace("Window ", "");
      const t = document.createElement("span"); t.className = "pt"; t.textContent = parts[1] || parts[0];
      if (parts.length > 2) { const sm = document.createElement("small"); sm.textContent = parts.slice(2).join(", "); t.appendChild(sm); }
      b.append(n, t);
      b.addEventListener("click", async () => {
        stopPlay(); state.w = k; if (!win().tracks[state.tr]) state.tr = Object.keys(win().tracks)[0];
        await enter(false);
      });
      pw.appendChild(b);
    }
    seg($("pick-track"), Object.entries(win().tracks).map(([k, v]) => [k, `Track ${k}, ${v.direction}`]), state.tr, async (t) => {
      state.tr = t; await enter(true);
    });
    for (const b of $("pick-pol").children) b.setAttribute("aria-pressed", String(b.dataset.pol === state.pol));
    $("mode-box").hidden = !win().camera;
    for (const b of $("pick-mode").children) b.setAttribute("aria-pressed", String(b.dataset.mode === state.mode));
  }

  /* Enter a window and track. Keeps the dates when they exist on the new track, else resets to the fire pair. */
  async function enter(resetDates) {
    await loadData();
    const d = trk().dates;
    if (resetDates || !d.includes(state.a) || !d.includes(state.b)) [state.a, state.b] = firePair();
    controls(); syncDates(); passPanel(); buildTimeline(); render();
  }

  async function render() {
    const seq = ++state.seq, P = state.pol.toUpperCase();
    const camMode = state.mode === "camera" && !!win().camera, cam = camMode ? win().camera[state.b] : null;
    $("tag-a").textContent = camMode ? (cam ? `Camera (${cam.sensor}): ${fmt(cam.hls_date)}` : "Camera: no pass") : `Before: ${fmt(state.a)}`;
    $("tag-b").textContent = camMode ? `Radar (${P}): ${fmt(state.b)}` : `After: ${fmt(state.b)}`;
    imgA.alt = camMode ? (cam ? `True-colour ${cam.sensor} image, ${fmt(cam.hls_date)}` : "No optical image") : `${P} radar image, ${fmt(state.a)}`;
    imgB.alt = `${P} radar image, ${fmt(state.b)}`;
    $("nocam").hidden = !camMode || !!cam;
    $("cam-note").hidden = !camMode;
    if (camMode) {
      const n = cam ? cam.days_apart : 0;
      const when = n === 0 ? "the same day as the radar pass" : `${Math.abs(n)} day${Math.abs(n) > 1 ? "s" : ""} ${n < 0 ? "before" : "after"} the radar pass`;
      $("cam-note").textContent = (cam
        ? `Left: what the optical satellite recorded on ${fmt(cam.hls_date)} (${cam.sensor}, ${when}), unmasked. ` +
          `Its own quality mask calls ${pct(cam.cloud)} of the window cloud (thick smoke is often classed as cloud). `
        : "") + `Right: the radar pass of ${fmt(state.b)}, with the change since ${fmt(state.a)}.`;
    }
    const d = trk().dates;
    ch = Score.change(cells, N, d.indexOf(state.a), d.indexOf(state.b), state.pol === "hv" ? 0 : 1, meta.cell_nodata);
    live(); series(); table(); syncDates(); markPass(); markTimeline();
    changeCanvas = null; draw();
    imgA.src = camMode ? (cam ? D + cam.file : BLANK) : src(state.a);
    imgB.src = src(state.b);
    try { if (!(await buildChange(seq))) return; } catch (e) { return; }
    draw();
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
  for (const b of $("pick-mode").children) b.addEventListener("click", () => { state.mode = b.dataset.mode; controls(); render(); });
  $("date-a").addEventListener("change", (e) => { stopPlay(); state.a = e.target.value; syncDates(); render(); });
  $("date-b").addEventListener("change", (e) => { stopPlay(); state.b = e.target.value; render(); });
  function step(k) {
    const later = trk().dates.filter((x) => x > state.a), i = later.indexOf(state.b) + k;
    if (i >= 0 && i < later.length) { state.b = later[i]; render(); }
  }
  $("prev-b").addEventListener("click", () => { stopPlay(); step(-1); });
  $("next-b").addEventListener("click", () => { stopPlay(); step(1); });
  $("preset-fire").addEventListener("click", () => { stopPlay(); [state.a, state.b] = firePair(); render(); });
  $("preset-placebo").addEventListener("click", () => { stopPlay(); [state.a, state.b] = placeboPair(); render(); });

  $("scale-note").textContent = "Each image is about 22 km across, north up. Dates are UTC. Brighter means a stronger radar echo.";
  state.tr = win().tracks["125"] ? "125" : Object.keys(win().tracks)[0];

  /* The claim in the app bar, from the peak period of the first window, so it cannot drift from the counts. */
  (function claim() {
    const info = win().passes; if (!info) return;
    const pk = info.periods[info.periods.length - 1];
    const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
    const u = WORDS[pk.usable] || String(pk.usable);
    const radar = pk.radar_ok === pk.radar ? `all ${pk.radar}` : `${pk.radar_ok} of ${pk.radar}`;
    $("claim").textContent = `At the peak of the fires, the optical satellites got ${u} usable look${pk.usable === 1 ? "" : "s"} in ${pk.optical} passes, and the radar got an image on ${radar}.`;
  })();

  /* First-visit hint, gone after the first drag. */
  let seen = false; try { seen = localStorage.getItem("wtccs-dragged") === "1"; } catch (e) { /* private mode */ }
  if (!seen) $("hint").hidden = false;
  $("viewer").addEventListener("pointerdown", () => { $("hint").hidden = true; try { localStorage.setItem("wtccs-dragged", "1"); } catch (e) { /* ignore */ } });

  /* One sweep on arrival: the divider starts at the right edge (all camera) and moves to the middle, uncovering the radar.
     Skipped for reduced motion, and stopped the moment the visitor touches the viewer. */
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let sweeping = !reduce;
  if (sweeping) { $("slide").value = 100; }
  slide();
  const stop = () => { sweeping = false; };
  $("viewer").addEventListener("pointerdown", stop, { once: true });
  $("slide").addEventListener("keydown", stop, { once: true });
  await enter(true);
  if (sweeping) {
    try { await Promise.all([imgA.decode(), imgB.decode()]); } catch (e) { /* show it anyway */ }
    await new Promise((r) => setTimeout(r, 350));
    const t0 = performance.now(), dur = 1500, from = 100, to = 50;
    const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
    (function frame(now) {
      if (!sweeping) return;
      const t = Math.min(1, (now - t0) / dur);
      $("slide").value = from + (to - from) * ease(t); slide();
      if (t < 1) requestAnimationFrame(frame); else sweeping = false;
    })(t0);
  }
})();
