/* Checks that the page's scoring (docs/score.js) gives the same numbers as the Python pipeline
   (docs/data/scores.json). Run: node tests/check_scores.cjs */
const fs = require("fs"), path = require("path");
const Score = require("../docs/score.js");
const D = path.join(__dirname, "..", "docs", "data");
const meta = JSON.parse(fs.readFileSync(path.join(D, "meta.json")));
const scores = JSON.parse(fs.readFileSync(path.join(D, "scores.json")));
const n = meta.ncell;
const r3 = (v) => (v === null ? null : Math.round(v * 1000) / 1000);
const r2 = (v) => (v === null ? null : Math.round(v * 100) / 100);
let checked = 0, bad = 0;

for (const rec of scores) {
  const wm = meta.windows[rec.window], tm = wm.tracks[String(rec.track)];
  const lb = fs.readFileSync(path.join(D, wm.optical.labels));
  const labels = new Uint8Array(lb.buffer, lb.byteOffset, lb.length);
  const cb = fs.readFileSync(path.join(D, tm.cells));
  const cells = new Int16Array(cb.buffer.slice(cb.byteOffset, cb.byteOffset + cb.length));
  for (const p of rec.pairs) {
    const iA = tm.dates.indexOf(p.from), iB = tm.dates.indexOf(p.to);
    ["hv", "hh"].forEach((pol, j) => {
      const s = Score.scorePair(Score.change(cells, n, iA, iB, j, meta.cell_nodata), labels, meta.rule_db);
      const pairs = [
        [r3(s.auc), p[pol + "_auc"]], [r3(s.aucSevere), p[pol + "_auc_severe"]],
        [s.flagged, p[pol + "_rule"].flagged], [r3(s.precision), p[pol + "_rule"].precision],
        [r3(s.falseAlarm), p[pol + "_rule"].false_alarm], [r3(s.recall), p[pol + "_rule"].recall],
        // medians can sit exactly on a half step, where Python and JavaScript round differently
        [r2(s.medianBurned), p[pol + "_median_burned"], 0.0101], [r2(s.medianUnburned), p[pol + "_median_unburned"], 0.0101],
      ];
      for (const [js, py, tol] of pairs) {
        checked++;
        const same = js === py || (js !== null && py !== null && Math.abs(js - py) <= (tol || 0.0011));
        if (!same) { bad++; console.log("MISMATCH", rec.window, rec.track, p.from, p.to, pol, js, py); }
      }
    });
  }
}
console.log(`${checked} values checked, ${bad} mismatches`);
process.exit(bad ? 1 : 0);
