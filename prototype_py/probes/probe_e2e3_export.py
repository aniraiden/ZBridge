# -*- coding: utf-8 -*-
"""probe_e2e3_export - S3 场景3 导出段（3 层 + 不同强度 + 层名 + SDiv>1）。
前置：当前子工具含 3 个图层（建议命名 LayerA/LayerB/LayerC，任意位置），
    且最好有细分级别（SDiv>1，可选但推荐）以验证细分切换/复原。
不再设置确定性状态：直接导出用户当前状态，并断言"导出后各层状态=导出前"（原状态不变），
    自检快照隔离 + layers.txt（强度/可见性原样记录）+ SDiv 复原。
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
    zb.log_init("s3_e2e3_export")
    os.makedirs(OUT_DIR, exist_ok=True)
    n = zb.layer_detect(zbc)
    if n != 3:
        zb.log("E2E", f"[FAIL] 需要 3 个图层，实际 {n}；请先在当前子工具上创建三个图层（建议命名 LayerA/LayerB/LayerC）后重跑")
        return
    st = zb.subtool_name(zbc)
    zb.log("E2E", f"subtool={st} layers={n}")
    sdiv_avail = zbc.exists("Tool:Geometry:SDiv") and zbc.is_enabled("Tool:Geometry:SDiv")
    cur0 = float(zbc.get("Tool:Geometry:SDiv")) if sdiv_avail else None
    if sdiv_avail:
        zb.log("E2E", f"sdiv cur={cur0} max={float(zbc.get_max('Tool:Geometry:SDiv'))}")
    else:
        zb.log("E2E", "sdiv n/a（当前物体无细分级别，SDiv 场景跳过）")
    # 记录导出前状态（栈顶->栈底；export_layers 不改变层序，可逐层比对）
    before = []
    zb.layer_goto_top(zbc, n)
    for i in range(n):
        before.append({"name": zb.layer_name(zbc),
                       "int": zb.layer_intensity(zbc),
                       "vis": zb.layer_visible(zbc)})
        if i < n - 1:
            zb.layer_step(zbc, down=True)
    names = [s["name"] for s in before]
    zb.log("E2E", f"layer names (栈顶->栈底): {names}")
    if len(set(names)) != n:
        zb.log("E2E", "[WARN] 图层名不唯一：快照可能不隔离，且同名层恢复可见性会命中栈顶")
    for i, s in enumerate(before):
        zb.log("E2E", f"before[{i}]: name={s['name']} int={s['int']} vis={s['vis']}")
    rec_n = zb.export_layers(zbc, OUT_DIR, st)
    zb.log("E2E", f"exported layers={rec_n}")
    if rec_n != 3:
        zb.log("E2E", "[FAIL] 导出记录数 != 3")
        return
    # 自检：快照隔离性 + layers.txt
    base = gozlib.read_goz_points(f"{OUT_DIR}/{st}_LayerBase.goz")[1]
    ds = [gozlib.vertex_delta(base, gozlib.read_goz_points(f"{OUT_DIR}/{st}_Layer{j}.goz")[1]) for j in range(3)]
    for j, d in enumerate(ds):
        zb.log("E2E", f"d{j}_norm={gozlib.delta_norm(d):.4f}")
    zb.log_pass("E2E", all(gozlib.delta_norm(d) > 1e-4 for d in ds), "三层快照均含真实形变（非空）")
    distinct = all(gozlib.residual_max(ds[a], ds[b]) > 1e-4 for a in range(3) for b in range(a + 1, 3))
    zb.log_pass("E2E", distinct, "三层快照互异（隔离）")
    recs = zb.read_layers_txt(f"{OUT_DIR}/layers.txt")
    zb.log_pass("E2E", len(recs) == 3, f"layers.txt 记录数=3（实际 {len(recs)}）")
    for r in sorted(recs, key=lambda x: x["idx"]):
        zb.log("E2E", f"rec idx={r['idx']} name={r['name']} int={r['intensity']} vis={r['visible']}")
    if sdiv_avail:
        zb.log_pass("E2E", abs(float(zbc.get("Tool:Geometry:SDiv")) - cur0) < 0.01,
                    f"导出后 SDiv 复原（{cur0}）")
    # 导出后状态比对（export_layers 已恢复原状态；层序=原序，逐层读）
    ok_restore = True
    zb.layer_goto_top(zbc, n)
    for i in range(n):
        got = {"name": zb.layer_name(zbc),
               "int": zb.layer_intensity(zbc),
               "vis": zb.layer_visible(zbc)}
        zb.log("E2E", f"after_export[{i}]: name={got['name']} int={got['int']} vis={got['vis']}")
        if abs(got["int"] - before[i]["int"]) > 0.01 or got["vis"] != before[i]["vis"]:
            ok_restore = False
        if i < n - 1:
            zb.layer_step(zbc, down=True)
    zb.log_pass("E2E", ok_restore, "导出后各层状态=导出前（原状态不变）")
    zb.log("E2E", "EXPORT_DONE")


run()
