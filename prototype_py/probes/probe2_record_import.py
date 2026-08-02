# -*- coding: utf-8 -*-
"""probe2_record_import - S2 录制导入验证（规格 §S2）。
验证：New(自动录制) -> 导入 L0.goz -> 形变是否进入新层（=delta(L0)）、基网格不变。
运行：ZBrush 2026.1 ZScript 面板 → Python Scripting → Load 加载本文件（加载即执行）。
前置：活动子工具无图层、拓扑与 out/L*.goz 一致（从 out/base.goz 导入生成）。
输出：log/zb085_*_s2_rec.log + 机器判定（与 S1 delta 交叉对比）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 强制真重新导入：ZBrush 解释器跨 Load 缓存旧模块（reload 在嵌入环境有风险，用 pop+import）
for _m in ("gozlib", "zbridge_085"):
    sys.modules.pop(_m, None)
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"   # 与 probe1 一致


def run():
    zb.log_init("s2_record_import")
    n0 = zb.layer_detect(zbc)
    zb.log("S2", f"before layers={n0}")
    if n0 != 0:
        zb.log("S2", "[FAIL] 前置要求：活动子工具必须无图层（先 Tool:Import out/base.goz）")
        return
    base = gozlib.read_goz_points(f"{OUT_DIR}/base.goz")[1]
    l0 = gozlib.read_goz_points(f"{OUT_DIR}/L0.goz")[1]
    expect_d = gozlib.vertex_delta(base, l0)

    zb.layer_record_import(zbc, f"{OUT_DIR}/L0.goz")
    zb.log("S2", f"after import layers={zb.layer_detect(zbc)} rec={zb.layer_recording(zbc)}")

    zb.export_goz(zbc, f"{OUT_DIR}/rec_out.goz")
    out_pts = gozlib.read_goz_points(f"{OUT_DIR}/rec_out.goz")[1]
    got_d = gozlib.vertex_delta(base, out_pts)
    resid = gozlib.residual_max(got_d, expect_d)
    zb.log("S2", f"delta residual vs expect: {resid:.6f}")
    eps = max(gozlib.delta_norm(expect_d) * 1e-3, 1e-4)
    zb.log_pass("S2", resid <= eps, "录制导入的形变应等于 S1 的 delta(L0)（交叉对比）")
    zb.log("S2", f"final layers={zb.layer_detect(zbc)} (应=1)")


if __name__ == "__main__":
    run()
