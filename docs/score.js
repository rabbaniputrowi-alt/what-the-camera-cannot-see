/* Scoring shared by the page and the Node check (tests/check_scores.cjs).
   Works on the integer cell values (dB x 100) so the browser and the Python pipeline agree exactly. */
(function (root) {
  "use strict";

  /* Chance that a random value from pos is larger than a random value from neg (ties count half). */
  function auc(pos, neg) {
    if (pos.length < 5 || neg.length < 5) return null;
    const all = new Array(pos.length + neg.length);
    for (let i = 0; i < pos.length; i++) all[i] = [pos[i], 1];
    for (let i = 0; i < neg.length; i++) all[pos.length + i] = [neg[i], 0];
    all.sort((a, b) => a[0] - b[0]);
    let sumPos = 0, i = 0;
    while (i < all.length) {
      let j = i;
      while (j + 1 < all.length && all[j + 1][0] === all[i][0]) j++;
      const rank = (i + j) / 2 + 1;               // average rank of the tied run
      for (let k = i; k <= j; k++) if (all[k][1]) sumPos += rank;
      i = j + 1;
    }
    return (sumPos - pos.length * (pos.length + 1) / 2) / (pos.length * neg.length);
  }

  function median(v) {
    if (!v.length) return null;
    const s = Array.from(v).sort((a, b) => a - b), m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }

  /* Change in dB x 100 between two dates for one polarization (0 = HV, 1 = HH). NaN where either is missing. */
  function change(cells, n, iA, iB, pol, nodata) {
    const size = n * n, a = (iA * 2 + pol) * size, b = (iB * 2 + pol) * size;
    const out = new Float32Array(size);
    for (let k = 0; k < size; k++) {
      const va = cells[a + k], vb = cells[b + k];
      out[k] = (va === nodata || vb === nodata) ? NaN : vb - va;
    }
    return out;
  }

  /* Score one date pair against the optical labels (1 unburned, 3 burned, 4 severely burned). */
  function scorePair(ch, labels, ruleDb) {
    const rule = Math.round(ruleDb * 100);
    const burned = [], severe = [], unb = [];
    let tp = 0, fp = 0, flagged = 0, nB = 0, nU = 0;
    for (let k = 0; k < ch.length; k++) {
      const d = ch[k];
      if (Number.isNaN(d)) continue;
      const flag = d <= rule, lab = labels[k];
      if (flag) flagged++;
      if (lab >= 3) { nB++; burned.push(-d); if (lab === 4) severe.push(-d); if (flag) tp++; }
      else if (lab === 1) { nU++; unb.push(-d); if (flag) fp++; }
    }
    const mb = median(burned), mu = median(unb);
    return {
      auc: auc(burned, unb), aucSevere: auc(severe, unb),
      medianBurned: mb === null ? null : -mb / 100, medianUnburned: mu === null ? null : -mu / 100,
      nBurned: nB, nUnburned: nU, flagged: flagged, flaggedBurned: tp, flaggedUnburned: fp,
      precision: tp + fp ? tp / (tp + fp) : null,
      falseAlarm: nU ? fp / nU : null,
      recall: nB ? tp / nB : null,
    };
  }

  const api = { auc: auc, median: median, change: change, scorePair: scorePair };
  root.Score = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
