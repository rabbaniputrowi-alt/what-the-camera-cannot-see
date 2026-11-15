"""Checks the pipeline's scoring on small inputs whose answers can be worked out by hand.

Usage: uv run python tests/test_score.py
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from score import auc, auc_fast, auc_interval, score_pair

A = np.array
# AUC: chance that a value from the first list is larger than one from the second, ties count half
assert auc(A([5, 6, 7, 8, 9]), A([0, 1, 2, 3, 4])) == 1.0
assert auc(A([0, 1, 2, 3, 4]), A([5, 6, 7, 8, 9])) == 0.0
assert auc(A([1, 2, 3, 4, 5]), A([1, 2, 3, 4, 5])) == 0.5
assert auc(A([7, 7, 7, 7, 7]), A([7, 7, 7, 7, 7])) == 0.5
assert auc(A([1, 3, 5, 7, 9]), A([2, 4, 6, 8, 10])) == 0.4        # 0 + 1 + 2 + 3 + 4 wins out of 25
assert auc(A([2, 2, 2, 2, 2]), A([1, 2, 2, 3, 3])) == 0.4        # each: 1 win and 2 ties, 2 out of 5
assert auc(A([1, 2, 3, 4]), A([0, 1, 2, 3, 4])) is None          # fewer than 5 cells: no score

# the fast version used for resampling gives the same number, ties included
rng = np.random.default_rng(1)
for _ in range(20):
    p, q = rng.integers(-300, 300, 200), rng.integers(-250, 350, 300)
    assert abs(auc_fast(p, q) - auc(p, q)) < 1e-6

# interval: fully separated groups give exactly 1, and the interval of a noisy case holds its own estimate
blk = np.arange(10) // 2
assert auc_interval(A([5, 6, 7, 8, 9, 10, 11, 12, 13, 14]), A(range(-10, 0)), blk, blk, 5,
                    np.random.default_rng(0), 200) == [1.0, 1.0]
p, q = rng.normal(0.5, 1, 400), rng.normal(0, 1, 400)
lo, hi = auc_interval(p, q, np.arange(400) // 20, np.arange(400) // 20, 20, np.random.default_rng(0), 300)
assert lo < auc(p, q) < hi and 0.02 < hi - lo < 0.3

# the rule on seven cells: change in dB x 100 and the optical label of each
NODATA = -32768
ch = [-200, -150, -50, 0, NODATA, -120, 30]
lab = A([[3, 4, 1, 1, 3, 1, 2]], "uint8")
a = np.zeros((2, 1, 7), "int16")
b = np.array([[ch], [ch]], "int16")
r = score_pair(a, b, lab, NODATA, -100)["hv_rule"]
assert r == {"flagged": 3, "flagged_burned": 2, "flagged_unburned": 1, "precision": 0.667, "false_alarm": 0.333,
             "recall": 1.0, "scored_share": 1.0, "base_rate": 0.4}, r
print("pipeline scoring: all checks passed")
