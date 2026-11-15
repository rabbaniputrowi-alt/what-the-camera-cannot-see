/* Demo deck: scaling, navigation, and the parts drawn from deck.json (pass strips, season curve, map). */
(() => {
  const slides = [...document.querySelectorAll(".slide")];
  const deck = document.getElementById("deck");
  const count = document.getElementById("count");
  const KEY = "wtccs-deck-slide";
  const motionOK = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  let cur = 0;

  slides.forEach((s, i) => {
    const pg = document.createElement("span");
    pg.className = "pg";
    pg.textContent = `${i + 1} / ${slides.length}`;
    s.appendChild(pg);
    s.id = `s${i + 1}`;
  });

  function fit() {
    const k = Math.min(innerWidth / 1920, innerHeight / 1080);
    deck.style.transform = `translate(${-960 * k}px, ${-540 * k}px) scale(${k})`;
  }
  function show(i) {
    cur = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach((s, j) => s.classList.toggle("on", j === cur));
    count.textContent = `${cur + 1} / ${slides.length}`;
    try { localStorage.setItem(KEY, String(cur)); } catch (e) { /* private mode */ }
    history.replaceState(null, "", `#${cur + 1}`);
  }
  addEventListener("resize", fit);
  addEventListener("keydown", (e) => {
    if (["ArrowRight", "PageDown", " ", "Enter"].includes(e.key)) { e.preventDefault(); show(cur + 1); }
    if (["ArrowLeft", "PageUp", "Backspace"].includes(e.key)) { e.preventDefault(); show(cur - 1); }
    if (e.key === "Home") show(0);
    if (e.key === "End") show(slides.length - 1);
  });
  document.getElementById("prev").onclick = () => show(cur - 1);
  document.getElementById("next").onclick = () => show(cur + 1);
  let x0 = null;
  addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  addEventListener("touchend", (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 40) show(cur + (dx < 0 ? 1 : -1));
  });

  const fromHash = parseInt(location.hash.slice(1), 10);
  let start = 0;
  if (fromHash >= 1) start = fromHash - 1;
  else { try { start = parseInt(localStorage.getItem(KEY) || "0", 10) || 0; } catch (e) { start = 0; } }
  fit(); show(start);

  /* Title slide: the divider sweeps slowly, like the slider on the page. */
  const wipe = document.querySelector(".wipe");
  if (motionOK && wipe) {
    const t0 = performance.now();
    (function step(t) {
      if (cur === 0) {
        const cut = 50 + 28 * Math.sin((t - t0) / 1900);
        wipe.style.setProperty("--cut", cut.toFixed(2) + "%");
      }
      requestAnimationFrame(step);
    })(t0);
  }

  const fmt = (d) => {
    const m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const [, mo, da] = d.split("-");
    return `${parseInt(da, 10)} ${m[parseInt(mo, 10) - 1]}`;
  };
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, parent, text) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (text !== undefined) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };

  fetch("deck.json").then((r) => r.json()).then((d) => {
    /* Slide 3: pass strips. */
    const so = document.getElementById("strip-opt");
    d.strip.optical.forEach((p) => {
      const t = document.createElement("div");
      t.className = "t" + (p.usable ? " ok" : "");
      const s2 = p.sensor === "Sentinel-2" ? "S2" : "Landsat";
      t.innerHTML = `<img src="${p.img}" alt="${p.sensor}, ${fmt(p.date)}"><span>${fmt(p.date)}, ${p.usable ? "usable" : s2}</span>`;
      so.appendChild(t);
    });
    const sr = document.getElementById("strip-rad");
    d.strip.radar.forEach((p) => {
      const t = document.createElement("div");
      t.className = "t";
      t.innerHTML = `<img src="${p.img}" alt="NISAR HV, ${fmt(p.date)}"><span>${fmt(p.date)}</span>`;
      sr.appendChild(t);
    });

    /* Slide 5: season curve for window 1, both orbits. */
    const svg = document.getElementById("curve");
    const L = 90, R = 880, T = 20, B = 500;
    const t0 = Date.parse("2026-06-15"), t1 = Date.parse("2026-11-08");
    const X = (d) => L + (Date.parse(d) - t0) / (t1 - t0) * (R - L);
    const Y = (v) => B - (v - 0.3) / 0.6 * (B - T);
    el("rect", { x: X("2026-09-15"), y: T, width: X("2026-11-01") - X("2026-09-15"), height: B - T, fill: "#1d1f31" }, svg);
    el("text", { x: X("2026-09-15") + 10, y: T + 30, fill: "#9a9fa6", "font-size": 20 }, svg, "Peak of the fires");
    [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9].forEach((v) => {
      el("line", { x1: L, x2: R, y1: Y(v), y2: Y(v), stroke: v === 0.5 ? "#9a9fa6" : "#2f3352", "stroke-width": v === 0.5 ? 2 : 1, "stroke-dasharray": v === 0.5 ? "8 6" : "" }, svg);
      el("text", { x: L - 14, y: Y(v) + 7, fill: "#9a9fa6", "font-size": 20, "text-anchor": "end" }, svg, v.toFixed(1));
    });
    el("text", { x: X("2026-06-17"), y: Y(0.5) + 28, fill: "#dfe1e2", "font-size": 20 }, svg, "0.50: no signal");
    ["2026-07-01", "2026-08-01", "2026-09-01", "2026-10-01", "2026-11-01"].forEach((m) => {
      el("line", { x1: X(m), x2: X(m), y1: B, y2: B + 8, stroke: "#4a4f75" }, svg);
      el("text", { x: X(m), y: B + 34, fill: "#9a9fa6", "font-size": 20, "text-anchor": "middle" }, svg, fmt(m));
    });
    const series = [["61", "#ff8266", 0.55, "Orbit 61"], ["125", "#e52207", 1, "Orbit 125"]];
    series.forEach(([trk, col, op, name]) => {
      const pts = d.curve[trk];
      const fire = pts.filter((p) => p.kind === "fire");
      el("polyline", { points: fire.map((p) => `${X(p.to)},${Y(p.hv)}`).join(" "), fill: "none", stroke: col, "stroke-width": 3, opacity: op }, svg);
      pts.forEach((p) => {
        el("circle", { cx: X(p.to), cy: Y(p.hv), r: 8, fill: p.kind === "fire" ? col : "#9a9fa6", opacity: p.kind === "fire" ? op : 1 }, svg);
      });
      const last = fire[fire.length - 1];
      const best = fire.reduce((a, b) => (b.hv > a.hv ? b : a));
      el("text", { x: X(best.to), y: Y(best.hv) - 18, fill: col, "font-size": 22, "font-weight": 600, "text-anchor": "middle", opacity: op < 1 ? 0.9 : 1 }, svg, `${best.hv.toFixed(2)}`);
      el("text", { x: X(last.to) + 14, y: Y(last.hv) + (trk === "61" ? 22 : -4), fill: col, "font-size": 19, opacity: op < 1 ? 0.9 : 1 }, svg, name);
    });

    /* Slide 6: map of the eight windows. */
    const map = document.getElementById("map");
    map.setAttribute("viewBox", "96 0 1056 400");
    fetch("land.svg").then((r) => r.text()).then((txt) => {
      const m = txt.match(/ d="([^"]+)"/);
      const land = el("path", { d: m ? m[1] : "", fill: "#282b45", stroke: "#4a4f75", "stroke-width": 1 });
      map.insertBefore(land, map.firstChild);
    });
    const verdict = { w1: "clean", w2: "hold", w3: "hold", w4: "hold", w5: "hold", w6: "weak", w7: "weak", w8: "fail" };
    const style = {
      clean: { fill: "#e7f434", stroke: "none", ink: "#e7f434" },
      hold: { fill: "#2491ff", stroke: "none", ink: "#ffffff" },
      weak: { fill: "#151622", stroke: "#9a9fa6", ink: "#dfe1e2" },
      fail: { fill: "#151622", stroke: "#ff8266", ink: "#ff8266" },
    };
    const off = { w1: [40, 52], w2: [-44, -46], w3: [46, -46], w4: [-56, 44], w5: [-30, -50], w6: [8, 58], w7: [-34, -50], w8: [-56, -44] };
    Object.entries(d.windows).forEach(([k, w]) => {
      const [lw, ls, le, ln] = w.bbox;
      const cx = ((lw + le) / 2 - 94) * 24, cy = (7 - (ls + ln) / 2) * 24;
      const s = style[verdict[k]];
      const [dx, dy] = off[k];
      el("line", { x1: cx, y1: cy, x2: cx + dx * 0.72, y2: cy + dy * 0.72, stroke: "#9a9fa6", "stroke-width": 1.5 }, map);
      el("circle", { cx, cy, r: 6.5, fill: s.fill, stroke: s.stroke, "stroke-width": 2.5 }, map);
      el("text", { x: cx + dx, y: cy + dy + 9, fill: s.ink, "font-size": 32, "font-weight": 800, "text-anchor": "middle" }, map, k.slice(1));
    });
    el("text", { x: 150, y: 110, fill: "#9a9fa6", "font-size": 22 }, map, "Sumatra");
    el("text", { x: 470, y: 120, fill: "#9a9fa6", "font-size": 22 }, map, "Kalimantan");
    el("text", { x: 1000, y: 300, fill: "#9a9fa6", "font-size": 22 }, map, "Papua");
  });
})();
