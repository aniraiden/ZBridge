# -*- coding: utf-8 -*-
"""probe1_isolation - S1 隔离性探测（规格 §S1）。
一次运行产出 5 项交叉指标：A 线性恒等式 / B 单层隔离 / D1 D2 污染诊断 / E 拓扑。
运行：ZBrush 2026.1 ZScript 面板 → Python Scripting → Load 加载本文件（加载即执行）。
前置：活动子工具含 2 层（LayerA@1、LayerB@0.5），形变互异明显。
输出：prototype_py/log/zb085_*_s1_isolation.log 末尾附结论。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"   # ← 用户可改为自己的测试目录
EXPECT_B_INT = 0.5


def run():
    zb.log_init("s1_isolation")
    os.makedirs(OUT_DIR, exist_ok=True)
    n = zb.layer_detect(zbc)
    zb.log("S1", f"layer_count={n}")
    if n != 2:
        zb.log("S1", f"[FAIL] 需要 2 个图层，实际 {n}；中止")
        return
    zb.layer_goto_top(zbc, n)
    zb.log("S1", f"top_layer={zb.layer_name(zbc)} int={zb.layer_intensity(zbc)}")

    # 快照序列：current -> base -> L0 -> L1
    zb.export_goz(zbc, f"{OUT_DIR}/cur.goz")           # 原状态 M
    zb.layer_goto_top(zbc, n)
    for i in range(n):                                  # 全部归零 -> base
        zb.layer_set_intensity(zbc, 0.0)
        if i < n - 1:
            zb.layer_step(zbc, down=True)
    zb.export_goz(zbc, f"{OUT_DIR}/base.goz")
    # 逐层快照：当前在栈底（LayerB）-> 导出 L1 -> 向上 LayerA -> 导出 L0
    zb.layer_set_visible(zbc, True)                     # 可见关阻断形变，必须先开眼
    zb.layer_set_intensity(zbc, 1.0)
    zb.export_goz(zbc, f"{OUT_DIR}/L1.goz")             # LayerB@1
    zb.layer_set_intensity(zbc, 0.0)                    # 置 0 防残留 + 自动关眼
    zb.layer_step(zbc, down=False)
    zb.layer_set_visible(zbc, True)
    zb.layer_set_intensity(zbc, 1.0)
    zb.export_goz(zbc, f"{OUT_DIR}/L0.goz")             # LayerA@1
    zb.layer_set_intensity(zbc, 0.0)

    # 机器判定（gozlib）
    cur = gozlib.read_goz_points(f"{OUT_DIR}/cur.goz")[1]
    base = gozlib.read_goz_points(f"{OUT_DIR}/base.goz")[1]
    l0 = gozlib.read_goz_points(f"{OUT_DIR}/L0.goz")[1]
    l1 = gozlib.read_goz_points(f"{OUT_DIR}/L1.goz")[1]
    m = gozlib.compute_metrics(cur, base, l0, l1, int0=1.0, int1=EXPECT_B_INT)
    for k, v in m.items():
        zb.log("S1", f"metric {k}={v}")
    zb.log("S1", "=== 结论 ===")
    zb.log("S1", f"A 线性叠加恒等式: {'PASS' if m['A_pass'] else 'FAIL'}")
    zb.log("S1", f"B 单层隔离:       {'PASS' if m['B_isolated'] else 'FAIL'}")
    zb.log("S1", f"E 拓扑一致:       {'PASS' if m['E_topology'] else 'FAIL'}")
    if not m["A_pass"]:
        zb.log("S1", f"D1 诊断(dB缺失? cur≈L0 残差): {m['D1_resid']:.6f}")
        zb.log("S1", f"D2 诊断(强度全1? cur≈L0+L1 残差): {m['D2_resid']:.6f}")
    zb.log("S1", f"OUT_DIR={OUT_DIR} 已生成 cur/base/L0/L1.goz")


if __name__ == "__main__":
    run()
