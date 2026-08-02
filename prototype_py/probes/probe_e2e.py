# -*- coding: utf-8 -*-
"""probe_e2e - S3 端到端验证（规格 §S3）：export -> 新会话 import -> 逐项断言 -> VERIFIED。
分两段运行（ZBrush 2026.1 -> ZScript 面板 -> Python Scripting -> Load 加载即执行）：
  第一段（默认）run_export()：当前子工具须含 2 个图层（建议命名 LayerA=栈底/LayerB=栈顶），
    脚本先设确定性状态（idx0: int=1.0 vis=True；idx1: int=1.0 vis=False），再 export_layers，
    脚本内自检快照文件（逐层 delta 非空互异）+ layers.txt 记录。
  第二段（argv 带 import）run_import()：用户新建会话并导入 <out>_LayerBase.goz 得到干净网格后，
    import_layers(全部记录)，导出 e2e_final.goz 与期望网格比对，输出 VERIFIED 报告。
输出：log/zb085_*_s3_e2e_*.log。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 强制真重新导入：ZBrush 解释器跨 Load 缓存旧模块（pop+import）
for _m in ("gozlib", "zbridge_085"):
    sys.modules.pop(_m, None)
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
# ZBrush Python Scripting 的 Load 无法传命令行参数：跑第二段前把这里改成 "import"
SEGMENT = "export"  # "export" | "import"


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


def _sdiv_max(zbc):
    """导出最终网格前切最高 SDiv（与快照拓扑一致）。"""
    try:
        if zbc.exists("Tool:Geometry:SDiv") and zbc.is_enabled("Tool:Geometry:SDiv"):
            zbc.set("Tool:Geometry:SDiv", zbc.get_max("Tool:Geometry:SDiv"))
    except Exception as e:
        zb.log("E2E", f"sdiv_max fail {type(e).__name__}: {e}")


def run_export():
    zb.log_init("s3_e2e_export")
    os.makedirs(OUT_DIR, exist_ok=True)
    n = zb.layer_detect(zbc)
    if n != 2:
        zb.log("E2E", f"[FAIL] 需要 2 个图层，实际 {n}；请先在当前子工具上创建两个图层（建议命名 LayerA/LayerB）后重跑")
        return
    st = zb.subtool_name(zbc)
    zb.log("E2E", f"subtool={st} layers={n}")
    # 设置确定性状态：idx0(栈底)=int 1.0 vis True；idx1(栈顶)=int 1.0 vis False
    zb.layer_goto_top(zbc, n)
    zb.layer_step(zbc, down=True)              # -> 栈底（idx0）
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, True)
    zb.layer_step(zbc, down=False)             # -> 栈顶（idx1）
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, False)
    zb.layer_log_state(zbc, "top(idx1)")
    names = []
    zb.layer_goto_top(zbc, n)
    for j in range(n):
        names.append(zb.layer_name(zbc))
        if j < n - 1:
            zb.layer_step(zbc, down=True)
    if len(set(names)) != n:
        zb.log("E2E", f"[WARN] 图层名不唯一 {names}：同名层记录/开眼将命中栈顶（首匹配陷阱），快照可能不隔离；建议重命名后重跑")
    # 导出
    rec_n = zb.export_layers(zbc, OUT_DIR, st)
    zb.log("E2E", f"exported layers={rec_n}")
    if rec_n != 2:
        zb.log("E2E", "[FAIL] 导出记录数 != 2")
        return
    # 自检：快照隔离性 + layers.txt
    base = gozlib.read_goz_points(f"{OUT_DIR}/{st}_LayerBase.goz")[1]
    d0 = gozlib.vertex_delta(base, gozlib.read_goz_points(f"{OUT_DIR}/{st}_Layer0.goz")[1])
    d1 = gozlib.vertex_delta(base, gozlib.read_goz_points(f"{OUT_DIR}/{st}_Layer1.goz")[1])
    zb.log("E2E", f"snapshot deltas: d0_norm={gozlib.delta_norm(d0):.4f} d1_norm={gozlib.delta_norm(d1):.4f}")
    zb.log_pass("E2E", gozlib.delta_norm(d0) > 1e-4 and gozlib.delta_norm(d1) > 1e-4,
                "两层快照均含真实形变（非空）")
    zb.log_pass("E2E", gozlib.residual_max(d0, d1) > 1e-4, "两层快照互异（隔离）")
    recs = zb.read_layers_txt(f"{OUT_DIR}/layers.txt")
    zb.log_pass("E2E", len(recs) == 2, f"layers.txt 记录数=2（实际 {len(recs)}）")
    for r in sorted(recs, key=lambda x: x["idx"]):
        zb.log("E2E", f"rec idx={r['idx']} name={r['name']} int={r['intensity']} vis={r['visible']}")
    # 导出后状态恢复（int 滑杆读回可靠；vis 唯一名可靠）
    zb.layer_goto_top(zbc, n)
    for j in range(n):
        zb.layer_log_state(zbc, f"after_export[{j}]")
        if j < n - 1:
            zb.layer_step(zbc, down=True)


def run_import():
    zb.log_init("s3_e2e_import")
    rebuilt, fails = zb.import_layers(zbc, OUT_DIR, None)
    if rebuilt == 0:
        zb.log("E2E", "[FAIL] 重建层数=0")
        return
    _sdiv_max(zbc)
    zb.export_goz(zbc, f"{OUT_DIR}/e2e_final.goz")
    final = gozlib.read_goz_points(f"{OUT_DIR}/e2e_final.goz")[1]
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
        zb.log("E2E", "[PASS] e2e_final = base + Σ vis×int×delta（可见性恢复 + 阻断语义成立）")
        verdict = "PASS"
    elif r_on <= eps:
        zb.log("E2E", "[WARN] e2e_final = base + Σ int×delta（可见性未阻断或未恢复）")
        verdict = "CHECK"
    else:
        zb.log("E2E", "[FAIL] 网格与两种期望均不符")
        verdict = "FAIL"
    n = zb.layer_detect(zbc)
    zb.log_pass("E2E", n == len(recs), f"final layer_count={n} 期望 {len(recs)}")
    zb.layer_goto_top(zbc, n)
    for j in range(n):
        zb.log("E2E", f"imported[{j}] name={zb.layer_name(zbc)} int={zb.layer_intensity(zbc)}")
        if j < n - 1:
            zb.layer_step(zbc, down=True)
    zb.log("E2E", f"VERIFIED={verdict} rebuilt={rebuilt} fails={fails}")


def run():
    try:
        # ZBrush 环境优先用 SEGMENT 开关；命令行（开发机）仍支持 sys.argv
        if SEGMENT == "import" or (len(sys.argv) > 1 and sys.argv[1] == "import"):
            run_import()
        else:
            run_export()
    except Exception as e:
        _fatal(e)


if __name__ == "__main__":
    run()
