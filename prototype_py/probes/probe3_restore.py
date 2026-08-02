# -*- coding: utf-8 -*-
"""probe3_restore v3 - S2 恢复算法验证（规格 §S2 probe3）。
核心流程：录制语义 = 导入网格 - 录制起点网格，故**每建一层前必须归零**。
建层顺序：先 L1（栈底）-> 归零 -> 再 L0（栈顶）。逐步 layer_log_state 记录状态。
v3 变更：弃用 importlib.reload（嵌入环境有风险），改模块级 sys.modules.pop+重新 import；
整个 run 包 try/except，任何异常写 log/zb085_fatal.log + 控制台 traceback；
指标前加读数守卫（gozlib 读 0 顶点 = 缓存旧版，中止判定）。
验证点：层数 / 全强度网格 = base+dA+dB / 层序（顶置 0 剩 base+dB）/ 强度写读往返。
运行：ZBrush 2026.1 ZScript 面板 → Python Scripting → Load 加载本文件。
前置：活动子工具无图层（从 out/base.goz 导入生成）。
输出：log/zb085_*_s3_restore.log + log/zb085_fatal.log（异常时）。"""
import os
import sys

print("probe3 loading...")          # 控制台可见性（需 Script Window Mode=Python Output）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 强制真重新导入：ZBrush 解释器跨 Load 缓存旧模块
for _m in ("gozlib", "zbridge_085"):
    sys.modules.pop(_m, None)
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")


def _fatal(exc):
    import traceback
    txt = "=== FATAL ===\n" + traceback.format_exc()
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "zb085_fatal.log"), "a", encoding="utf-8") as f:
            f.write(txt + "\n")
    except Exception:
        pass
    print(txt)


def run():
    try:
        _run()
    except Exception as e:
        _fatal(e)


def _run():
    zb.log_init("s3_restore")
    base = gozlib.read_goz_points(f"{OUT_DIR}/base.goz")[1]
    l0 = gozlib.read_goz_points(f"{OUT_DIR}/L0.goz")[1]
    l1 = gozlib.read_goz_points(f"{OUT_DIR}/L1.goz")[1]
    counts = (len(base), len(l0), len(l1))
    zb.log("RST", f"read counts={counts}")
    if min(counts) == 0:
        zb.log("RST", "[FAIL] gozlib 读数=0，疑似旧版缓存（tag=10000）；中止判定")
        return
    dA = gozlib.vertex_delta(base, l0)
    dB = gozlib.vertex_delta(base, l1)
    zb.log("RST", f"expect: dA_norm={gozlib.delta_norm(dA):.4f} dB_norm={gozlib.delta_norm(dB):.4f}")

    n0 = zb.layer_detect(zbc)
    zb.log_pass("RST", n0 == 0, f"前置：活动子工具应无图层（实际 {n0}）")
    if n0 != 0:
        return

    # 1) 先建 LayerB（栈底，New 插栈顶=当前唯一层）
    ok1, e1 = zb.layer_record_import(zbc, f"{OUT_DIR}/L1.goz")
    zb.layer_log_state(zbc, f"built B ok={ok1} e={e1}")
    # 2) 归零 B -> 网格回 base（强度0自动关眼）
    zb.layer_set_intensity(zbc, 0.0)
    zb.layer_log_state(zbc, "after zero B")
    # 3) 再建 LayerA（栈顶）-> 录得 dA
    ok2, e2 = zb.layer_record_import(zbc, f"{OUT_DIR}/L0.goz")
    zb.layer_log_state(zbc, f"built A ok={ok2} e={e2}")
    n = zb.layer_detect(zbc)
    zb.log_pass("RST", n == 2, f"层数应=2，实际 {n}")
    if n != 2:
        return
    # 4) 恢复 LayerB：导航下移（验证选中层）-> 强度1 -> 开眼
    zb.layer_step(zbc, down=True)
    zb.layer_log_state(zbc, "after step down (应=B)")
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, True)
    zb.layer_log_state(zbc, "after restore B")
    # 5) 全强度网格 = B + dA + dB（与 S1 delta 交叉对比）
    zb.layer_goto_top(zbc, n)
    zb.layer_log_state(zbc, "after goto top")
    zb.export_goz(zbc, f"{OUT_DIR}/restore_full.goz")
    full = gozlib.read_goz_points(f"{OUT_DIR}/restore_full.goz")[1]
    expect_full = gozlib.add_pts(gozlib.add_pts(base, dA), dB)
    resid = gozlib.residual_max(full, expect_full)
    zb.log("RST", f"full-stack residual={resid:.6f} (count={len(full)})")
    zb.log_pass("RST", len(full) == len(base) and resid <= max(gozlib.delta_norm(expect_full) * 1e-3, 1e-4),
                "双录层重建后网格 = B + dA + dB（与 S1 delta 交叉对比）")
    # 6) 层序交叉：此刻在栈顶（应为 A=dA），置顶 0 -> 剩 base+dB（若 New 插栈顶成立）
    zb.layer_set_intensity(zbc, 0.0)
    zb.export_goz(zbc, f"{OUT_DIR}/restore_top0.goz")
    top0 = gozlib.read_goz_points(f"{OUT_DIR}/restore_top0.goz")[1]
    resid_order = gozlib.residual_max(top0, gozlib.add_pts(base, dB))
    zb.log("RST", f"top-zero residual vs base+dB: {resid_order:.6f} (count={len(top0)})")
    zb.log_pass("RST", len(top0) == len(base) and resid_order <= max(gozlib.delta_norm(dB) * 1e-3, 1e-4),
                "栈顶=A(dA)，New 插栈顶成立（剩底层 B=dB）")
    # 7) 恢复栈顶层强度 + 开眼，做强度写读往返
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, True)
    zb.layer_log_state(zbc, "after restore A")
    zb.layer_set_intensity(zbc, 0.5)
    readback = zb.layer_intensity(zbc)
    zb.log("RST", f"set A=0.5 read_back={readback}")
    zb.log_pass("RST", abs(readback - 0.5) < 1e-6, "强度写读往返")
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, True)
    zb.layer_log_state(zbc, "final state")


if __name__ == "__main__":
    run()
