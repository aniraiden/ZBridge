# -*- coding: utf-8 -*-
"""v5 网格组成分析：对 out/ 下 v5 导出的网格做精确残差矩阵，定位网格=哪种组合。"""
import sys
sys.path.insert(0, r"h:/vibe_coding/ZBridge/prototype_py")
import gozlib

OUT = r"h:/vibe_coding/ZBridge/prototype_py/out"

base = gozlib.read_goz_points(f"{OUT}/base.goz")[1]
l0 = gozlib.read_goz_points(f"{OUT}/L0.goz")[1]
l1 = gozlib.read_goz_points(f"{OUT}/L1.goz")[1]
dA = gozlib.vertex_delta(base, l0)
dB = gozlib.vertex_delta(base, l1)

def add(*deltas):
    pts = base
    for d in deltas:
        pts = gozlib.add_pts(pts, d)
    return pts

candidates = {
    "base": base,
    "base+dA": add(dA),
    "base+dB": add(dB),
    "base+dA+dB": add(dA, dB),
    "base+dA-dB": add(dA, [(-x, -y, -z) for x, y, z in dB]),
    "base-dA+dB": add([(-x, -y, -z) for x, y, z in dA], dB),
    "base+dA+0.5dB": add(dA, gozlib.add_scaled(dB, 0.5)),
    "base+0.5dA+dB": add(gozlib.add_scaled(dA, 0.5), dB),
    "L0": l0, "L1": l1,
}

targets = ["a_diag.goz", "restore_full.goz", "restore_top0.goz"]
for t in targets:
    m = gozlib.read_goz_points(f"{OUT}/{t}")[1]
    print(f"=== {t} (count={len(m)}) ===")
    rows = []
    for name, cand in candidates.items():
        r = gozlib.residual_max(m, cand)
        rows.append((r, name))
    rows.sort()
    for r, name in rows[:6]:
        print(f"  {name:20s} resid={r:.6f}")
