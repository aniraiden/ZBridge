# -*- coding: utf-8 -*-
"""probe3_restore - S2 恢复算法验证（规格 §S2 probe3）。
核心流程（2026-08-02 修正）：录制语义 = 导入网格 - 录制起点网格，故**每建一层前必须归零**，
否则后建层 delta 被污染（如 dA-dB）。建层顺序：先 L1（栈底）-> 归零 -> 再 L0（栈顶，New 插栈顶）。
验证点：层数 / 双录层全强度网格 = base+dA+dB / 层序（顶置 0 剩 base+dB）/ 强度写读往返。
运行：ZBrush 2026.1 ZScript 面板 → Python Scripting → Load 加载本文件。
前置：probe2 通过；活动子工具无图层（从 out/base.goz 导入生成）。
输出：log/zb085_*_s3_restore.log + 机器判定。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"


def run():
    zb.log_init("s3_restore")
    base = gozlib.read_goz_points(f"{OUT_DIR}/base.goz")[1]
    l0 = gozlib.read_goz_points(f"{OUT_DIR}/L0.goz")[1]
    l1 = gozlib.read_goz_points(f"{OUT_DIR}/L1.goz")[1]
    dA = gozlib.vertex_delta(base, l0)
    dB = gozlib.vertex_delta(base, l1)

    # 1) 先建 LayerB（栈底，New 插栈顶=当前唯一层）-> 归零 -> 网格回 base
    ok1, e1 = zb.layer_record_import(zbc, f"{OUT_DIR}/L1.goz")
    zb.log("RST", f"after L1 import: cur_layer={zb.layer_name(zbc)} int={zb.layer_intensity(zbc)}")
    zb.layer_set_intensity(zbc, 0.0)                     # 强度0自动关眼，网格回 base
    # 2) 再建 LayerA（栈顶）-> 录得 dA
    ok2, e2 = zb.layer_record_import(zbc, f"{OUT_DIR}/L0.goz")
    zb.log("RST", f"record_import results: {ok1}/{e1} {ok2}/{e2}")
    n = zb.layer_detect(zbc)
    zb.log_pass("RST", n == 2, f"层数应=2，实际 {n}")
    if n != 2:
        return
    # 3) 恢复 LayerB：导航下移 -> 强度1 -> 开眼（强度0时眼已关，须显式重开）
    zb.layer_step(zbc, down=True)
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, True)
    # 4) 全强度网格 = B + dA + dB（与 S1 delta 交叉对比）
    zb.layer_goto_top(zbc, n)
    zb.export_goz(zbc, f"{OUT_DIR}/restore_full.goz")
    full = gozlib.read_goz_points(f"{OUT_DIR}/restore_full.goz")[1]
    expect_full = gozlib.add_pts(gozlib.add_pts(base, dA), dB)
    resid = gozlib.residual_max(full, expect_full)
    zb.log("RST", f"full-stack residual={resid:.6f}")
    zb.log_pass("RST", resid <= max(gozlib.delta_norm(expect_full) * 1e-3, 1e-4),
                "双录层重建后网格 = B + dA + dB（与 S1 delta 交叉对比）")
    # 5) 层序交叉：此刻在栈顶（应为 A=dA），置顶 0 -> 剩 base+dB（若 New 插栈顶成立）
    zb.layer_set_intensity(zbc, 0.0)
    zb.export_goz(zbc, f"{OUT_DIR}/restore_top0.goz")
    top0 = gozlib.read_goz_points(f"{OUT_DIR}/restore_top0.goz")[1]
    resid_order = gozlib.residual_max(top0, gozlib.add_pts(base, dB))
    zb.log("RST", f"top-zero residual vs base+dB: {resid_order:.6f}")
    zb.log_pass("RST", resid_order <= max(gozlib.delta_norm(dB) * 1e-3, 1e-4),
                "栈顶=A(dA)，New 插栈顶成立（剩底层 B=dB）")
    # 6) 恢复栈顶层强度 + 开眼，做强度写读往返
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, True)
    zb.layer_set_intensity(zbc, 0.5)
    readback = zb.layer_intensity(zbc)
    zb.log("RST", f"set A=0.5 read_back={readback}")
    zb.log_pass("RST", abs(readback - 0.5) < 1e-6, "强度写读往返")
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, True)


if __name__ == "__main__":
    run()
