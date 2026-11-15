/* Checks the page's scoring (docs/score.js) on small inputs whose answers can be worked out by hand.
   Run: node tests/test_score.cjs */
const assert = require("assert");
const Score = require("../docs/score.js");

// AUC: chance that a value from the first list is larger than one from the second, ties count half
assert.strictEqual(Score.auc([5, 6, 7, 8, 9], [0, 1, 2, 3, 4]), 1);
assert.strictEqual(Score.auc([0, 1, 2, 3, 4], [5, 6, 7, 8, 9]), 0);
assert.strictEqual(Score.auc([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]), 0.5);
assert.strictEqual(Score.auc([7, 7, 7, 7, 7], [7, 7, 7, 7, 7]), 0.5);
assert.strictEqual(Score.auc([1, 3, 5, 7, 9], [2, 4, 6, 8, 10]), 0.4);   // 0 + 1 + 2 + 3 + 4 wins out of 25
assert.strictEqual(Score.auc([2, 2, 2, 2, 2], [1, 2, 2, 3, 3]), 0.4);    // each: 1 win and 2 ties, 2 out of 5
assert.strictEqual(Score.auc([1, 2, 3, 4], [0, 1, 2, 3, 4]), null);      // fewer than 5 cells: no score

assert.strictEqual(Score.median([3, 1, 2]), 2);
assert.strictEqual(Score.median([4, 1, 3, 2]), 2.5);
assert.strictEqual(Score.median([]), null);

// change between two dates on a 2 by 2 grid. Order in the file: date, polarization (HV, HH), cell.
const NODATA = -32768;
const cells = new Int16Array([
  100, NODATA, 0, 50,      /* date 0, HV */   1, 1, 1, 1,   /* date 0, HH */
  -50, 200, NODATA, 50,    /* date 1, HV */   4, 4, 4, 4,   /* date 1, HH */
]);
const hv = Score.change(cells, 2, 0, 1, 0, NODATA);
assert.strictEqual(hv[0], -150);
assert.ok(Number.isNaN(hv[1]) && Number.isNaN(hv[2]));                   // missing on either date
assert.strictEqual(hv[3], 0);
assert.deepStrictEqual(Array.from(Score.change(cells, 2, 0, 1, 1, NODATA)), [3, 3, 3, 3]);

// the rule on seven cells: change in dB x 100 and the optical label of each
const s = Score.scorePair(new Float32Array([-200, -150, -50, 0, NaN, -120, 30]), [3, 4, 1, 1, 3, 1, 2], -1);
assert.deepStrictEqual(
  [s.flagged, s.flaggedBurned, s.flaggedUnburned, s.nBurned, s.nUnburned], [3, 2, 1, 2, 3]);
assert.strictEqual(s.precision, 2 / 3);
assert.strictEqual(s.falseAlarm, 1 / 3);
assert.strictEqual(s.recall, 1);
assert.strictEqual(s.auc, null);
assert.strictEqual(s.medianBurned, -1.75);
assert.strictEqual(s.medianUnburned, -0.5);
console.log("page scoring: all checks passed");
