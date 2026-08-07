# -*- coding: utf-8 -*-
"""probe_e2e3_import - S3 场景3 导入段（3 层 + 不同强度 + 层名 + SDiv>1）。
前置：新会话中把 out/<subtool>_LayerBase.goz 导入 ZBrush（干净网格、无图层），
    再 Load 本文件：import_layers(全部记录) -> 导出 e2e3_final.goz 与期望网格比对 ->
    核对层数/层名/强度/可见性/SDiv 复原 -> VERIFIED 报告。
运行：ZScript 面板 -> Python Scripting -> Load 本文件。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _m in ("gozlib", "zbridge_085"):
    sys.modules.pop(_m, None)
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"


def run():
    zb.log_init("s3_e2e3_import")
    sdiv_avail = zbc.exists("Tool:Geometry:SDiv") and zbc.is_enabled("Tool:Geometry:SDiv")
    sdiv0 = float(zbc.get("Tool:Geometry:SDiv")) if sdiv_avail else None
    if sdiv0 is not None:
        zb.log("E2E", f"sdiv before={sdiv0} max={float(zbc.get_max('Tool:Geometry:SDiv'))}")
    rebuilt, fails = zb.import_layers(zbc, OUT_DIR, None)
    if rebuilt == 0:
        zb.log("E2E", "[FAIL] 重建层数=0")
        return
    _sdiv_max(zbc)
    zb.export_goz(zbc, f"{OUT_DIR}/e2e3_final.goz")
    final = gozlib.read_goz_points(f"{OUT_DIR}/e2e3_final.goz")[1]
    recs = zb.read_layers_txt(f"{OUT_DIR}/layers.txt")
    st = recs[0]["subtool"] if recs else ""
    exp_on = zb.expected_mesh(OUT_DIR, st, recs, vis_blocks=False)
    exp_off = zb.expected_mesh(OUT_DIR, st, recs, vis_blocks=True)
    if exp_on is None or exp_off is None:
        zb.log("E2E", "[FAIL] 期望网格缺快照文件（LayerBase/Layer<i>.goz）")
        return
    r_on = gozlib.residual_max(final, exp_on)
    r_off = gozlib.residual_max(final, exp_off)
    zb.log("E2E", f"final vs expected(全计):   resid={r_on:.6f}")
    zb.log("E2E", f"final vs expected(vis阻断): resid={r_off:.6f}")
    eps = max(gozlib.delta_norm(gozlib.vertex_delta(exp_off, exp_on)) * 1e-3, 1e-4)
    if r_off <= eps:
        zb.log("E2E", "[PASS] e2e3_final = base + Σ vis×int×delta（可见性 + 强度 + 阻断语义成立）")
        verdict = "PASS"
    elif r_on <= eps:
        zb.log("E2E", "[WARN] e2e3_final = base + Σ int×delta（可见性未阻断或未恢复）")
        verdict = "CHECK"
    else:
        zb.log("E2E", "[FAIL] 网格与两种期望均不符")
        verdict = "FAIL"
    n = zb.layer_detect(zbc)
    zb.log_pass("E2E", n == len(recs), f"final layer_count={n} 期望 {len(recs)}")
    # 层名/强度/可见性逐层核对（栈顶=idx 最大 -> 向下）。
    # 重名层按名寻址恒命中栈顶：核对须逐层 MoveUp 到栈顶读取（同恢复 pass 机制），否则误读栈顶。
    by_idx = {r["idx"]: r for r in recs}
    ok_int = ok_vis = True
    zb.layer_goto_top(zbc, n)
    for j in range(n):
        idx = n - 1 - j
        r = by_idx[idx]
        for _ in range(n - 1):
            zb.layer_step(zbc, down=True)   # 到栈底（未核对的最下层）
        for _ in range(n - 1):
            zbc.press("Tool:Layers:MoveUp")  # 移到栈顶（首匹配=本层）
        got_name = zb.layer_name(zbc)
        got_int = zb.layer_intensity(zbc)
        got_vis = zb.layer_visible(zbc)
        zb.log("E2E", f"imported[{j}] idx={idx} expect(name={r['name']} int={r['intensity']} vis={r['visible']}) "
                      f"got(name={got_name} int={got_int} vis={got_vis})")
        if abs(got_int - r["intensity"]) > 0.01:
            ok_int = False
        if got_vis != r["visible"]:
            ok_vis = False
    zb.log("E2E", "层名恢复：未启用重命名（2026.1 Tool:Layers:Rename 弹模态框阻塞脚本、FileNameSetNext 无效、"
                  "Python 无 DLL 接口；层名恢复留待 S4 ZScript 版用 ZFU DLL）")
    zb.log_pass("E2E", ok_int, "强度恢复（全部与记录一致）")
    zb.log_pass("E2E", ok_vis, "可见性恢复（全部与记录一致）")
    if sdiv0 is not None:
        zb.log_pass("E2E", abs(float(zbc.get("Tool:Geometry:SDiv")) - sdiv0) < 0.01,
                    f"导入后 SDiv 复原（{sdiv0}）")
    zb.log("E2E", f"VERIFIED={verdict} rebuilt={rebuilt} fails={fails}")


def _sdiv_max(zbc):
    try:
        if zbc.exists("Tool:Geometry:SDiv") and zbc.is_enabled("Tool:Geometry:SDiv"):
            zbc.set("Tool:Geometry:SDiv", zbc.get_max("Tool:Geometry:SDiv"))
    except Exception as e:
        zb.log("E2E", f"sdiv_max fail {type(e).__name__}: {e}")


run()
