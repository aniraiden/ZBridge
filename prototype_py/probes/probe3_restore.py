# -*- coding: utf-8 -*-
"""probe3_restore v5 - S2 恢复算法验证（规格 §S2 probe3）。
v3/v4 定位结论：
  1. IModGet 读 rec 位**不可靠**（design_next probe4k："前后对比无法可靠检测录制态"）——
     v3/v4 的 A 层空白真因是 layer_record_import 以 rec 读为"门"，第二次 New 读到假
     阴性（False）就跳过导入，并非 New 不录制；参考文档明确 "New 创建后自动进入录制"，
     用户肉眼（"最后一个是录制状态"）亦证实。
  2. Tool:Import 在存在**录制层**时无效/被阻塞（v4 的 V0 轮 New 后未退录制，后续 3 轮
     重置导入全被阻塞、图层逐轮累积成 4 层，全空）。
v5 变更：
  - 彻底移除 rec 读门：New -> 导入 -> W-25 退录制点击（New 必录制故方向安全）；
    层存活用 layer_detect 计数验证（New 后 +1 / Import 后不变，防"工具被替换"灾难）。
  - 开眼用确定性序列（零读依赖）：置 0（自动关眼）-> IClick W-5 开 -> 恢复强度。
  - 重置：逐层 Delete 清栈 + Tool:Import base.goz，计数验证 0 层。
  - 验证全部走网格导出（base+dA+dB / base+dA / base+dB 残差），不信读回。
验证点：层数 / a_diag=A 捕获 dA / 全强度网格 = base+dA+dB / 层序 / 强度写读往返。
运行：ZBrush 2026.1 ZScript 面板 -> Python Scripting -> Load 加载本文件。
前置：活动子工具任意状态（脚本自动清理图层并导入 base.goz 重置）。"""
import os
import sys
import time

print("probe3 v5 loading...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


def _reset_clean():
    """尽力清空图层栈并导入 base.goz。返回 True 当且仅当最终 0 图层。
    策略：①直接导入（场景已干净时一步到位）；②逐层 Delete 清栈（杀掉录制态）后导入；
    ③当前层 W-25 退录制后导入。每步计数验证。"""
    for step in ("direct", "delete", "w25"):
        if step == "direct":
            pass
        elif step == "delete":
            try:
                n = zb.layer_detect(zbc)
                for _ in range(n + 2):
                    zbc.press("Tool:Layers:Delete")
                    time.sleep(0.05)
                zb.log("RST", f"reset: delete 兜底（原 {n} 层）")
            except Exception as e:
                zb.log("RST", f"reset: delete 抛错 {type(e).__name__}: {e}")
        elif step == "w25":
            try:
                p = zb.layer_full_path(zbc)
                zbc.click(p, zbc.get_width(p) - 25, zbc.get_height(p) / 2)
                zb.log("RST", "reset: W-25 退录制点击")
            except Exception as e:
                zb.log("RST", f"reset: w25 抛错 {type(e).__name__}: {e}")
        zbc.set_next_filename(f"{OUT_DIR}/base.goz".replace("\\", "/"))
        zbc.press("Tool:Import")
        time.sleep(0.3)
        if zb.layer_detect(zbc) == 0:
            zb.log("RST", f"[PASS] 重置成功（{step}）：0 图层")
            return True
        zb.log("RST", f"[WARN] 重置（{step}）后仍有余层")
    zb.log("RST", "[FAIL] 重置失败：图层栈未清空；请手动删除全部层后重跑")
    return False


def _eye_force_on(tag):
    """确定性开眼：置 0（自动关眼，已知态）-> IClick W-5 开 -> 恢复原强度。零读依赖。"""
    try:
        cur = zb.layer_intensity(zbc)
    except Exception:
        cur = 1.0
    zbc.set("Tool:Layers:Layer Intensity", 0.0)
    p = zb.layer_full_path(zbc)
    zbc.click(p, zbc.get_width(p) - 5, zbc.get_height(p) / 2)
    time.sleep(0.05)
    zbc.set("Tool:Layers:Layer Intensity", cur if cur else 1.0)
    zb.log("LAYER", f"{tag}:eye force-on (int 0->click->{cur})")


def _layer_import(goz_path, tag):
    """New -> 导入 goz_path -> W-25 退录制。不做 rec 读门（New 必录制）。
    层存活验证：New 后层数>0、Import 后层数不变（防 Import 替换工具清层）。
    返回 (ok, err, count_after_import)。"""
    zb.layer_log_state(zbc, f"{tag}:before")
    zbc.press("Tool:Layers:New")
    zb.layer_log_state(zbc, f"{tag}:after_New")
    if zb.layer_detect(zbc) == 0:
        zb.log("LAYER", f"[FAIL] {tag}: New 后层数=0，中止")
        return False, "new_noop", 0
    zbc.set_next_filename(goz_path.replace("\\", "/"))
    zbc.press("Tool:Import")
    time.sleep(0.2)
    zb.layer_log_state(zbc, f"{tag}:after_Import")
    n = zb.layer_detect(zbc)
    if n == 0:
        zb.log("LAYER", f"[FAIL] {tag}: Import 后层数=0（工具被替换），中止")
        return False, "tool_replaced", 0
    try:
        p = zb.layer_full_path(zbc)
        zbc.click(p, zbc.get_width(p) - 25, zbc.get_height(p) / 2)
        zb.layer_log_state(zbc, f"{tag}:after_exit_click")
    except Exception as e:
        zb.log("LAYER", f"{tag}:exit click fail {type(e).__name__}: {e}")
        return False, f"exit_click:{type(e).__name__}", n
    return True, "", n


def _run():
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

    if not _reset_clean():
        return

    # 1) 建 LayerB（栈底）：New -> 导入 L1 -> 退录制
    ok1, e1, nB = _layer_import(f"{OUT_DIR}/L1.goz", "B")
    if not ok1:
        return
    zb.log_pass("RST", nB == 1, f"B 建层后层数应=1（实际 {nB}）")
    # 2) 归零 B：网格回 base + 自动关眼（+文档化退录制兜底）
    zbc.set("Tool:Layers:Layer Intensity", 0.0)
    zb.layer_log_state(zbc, "after zero B")

    # 3) 建 LayerA（栈顶）：New -> 导入 L0 -> 退录制。★ 关键：第二次 New+导入能否录得 dA
    ok2, e2, nA = _layer_import(f"{OUT_DIR}/L0.goz", "A")
    if not ok2:
        return
    zb.log_pass("RST", nA == 2, f"A 建层后层数应=2（实际 {nA}）")

    # 4) a_diag：此刻 B@0，A@1；确定性开 A 眼后导出，应 = base+dA
    _eye_force_on("a_diag")
    zb.export_goz(zbc, f"{OUT_DIR}/a_diag.goz")
    diag = gozlib.read_goz_points(f"{OUT_DIR}/a_diag.goz")[1]
    r_diag = gozlib.residual_max(diag, gozlib.add_pts(base, dA))
    r_base = gozlib.residual_max(diag, base)
    zb.log("RST", f"a_diag: vs base+dA={r_diag:.6f} vs base={r_base:.6f} (count={len(diag)})")
    zb.log_pass("RST", len(diag) == len(base) and r_diag <= max(gozlib.delta_norm(dA) * 1e-3, 1e-4),
                "第二次 New+导入捕获 dA（A 层有内容且开眼）")

    # 5) 完整恢复：导航到 B -> B@1 + 开眼 -> 回 A -> A@1 + 开眼 -> 导出，应 = base+dA+dB
    zb.layer_step(zbc, down=True)
    zb.layer_log_state(zbc, "after step down (应=B)")
    zbc.set("Tool:Layers:Layer Intensity", 1.0)
    _eye_force_on("restore B")
    zb.layer_step(zbc, down=False)
    zb.layer_log_state(zbc, "after step up (应=A)")
    zbc.set("Tool:Layers:Layer Intensity", 1.0)
    _eye_force_on("restore A")
    zb.export_goz(zbc, f"{OUT_DIR}/restore_full.goz")
    full = gozlib.read_goz_points(f"{OUT_DIR}/restore_full.goz")[1]
    expect_full = gozlib.add_pts(gozlib.add_pts(base, dA), dB)
    resid = gozlib.residual_max(full, expect_full)
    zb.log("RST", f"full-stack residual={resid:.6f} (count={len(full)})")
    zb.log_pass("RST", len(full) == len(base) and resid <= max(gozlib.delta_norm(expect_full) * 1e-3, 1e-4),
                "全强度网格 = base+dA+dB（双录层重建成功）")

    # 6) 层序交叉：此刻在栈顶（应=A），A 置 0 -> 剩 base+dB（New 插栈顶成立）
    zbc.set("Tool:Layers:Layer Intensity", 0.0)
    zb.export_goz(zbc, f"{OUT_DIR}/restore_top0.goz")
    top0 = gozlib.read_goz_points(f"{OUT_DIR}/restore_top0.goz")[1]
    resid_order = gozlib.residual_max(top0, gozlib.add_pts(base, dB))
    zb.log("RST", f"top-zero residual vs base+dB: {resid_order:.6f} (count={len(top0)})")
    zb.log_pass("RST", len(top0) == len(base) and resid_order <= max(gozlib.delta_norm(dB) * 1e-3, 1e-4),
                "栈顶=A(dA)，New 插栈顶成立（剩底层 B=dB）")

    # 7) 恢复栈顶层强度 + 开眼，做强度写读往返
    zbc.set("Tool:Layers:Layer Intensity", 1.0)
    _eye_force_on("restore A2")
    zb.layer_log_state(zbc, "after restore A")
    zbc.set("Tool:Layers:Layer Intensity", 0.5)
    readback = zb.layer_intensity(zbc)
    zb.log("RST", f"set A=0.5 read_back={readback}")
    zb.log_pass("RST", abs(readback - 0.5) < 1e-6, "强度写读往返")
    zbc.set("Tool:Layers:Layer Intensity", 1.0)
    _eye_force_on("final A")
    zb.layer_log_state(zbc, "final state")


def run():
    try:
        zb.log_init("s3_restore")
        _run()
    except Exception as e:
        _fatal(e)


if __name__ == "__main__":
    run()
