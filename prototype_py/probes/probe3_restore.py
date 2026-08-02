# -*- coding: utf-8 -*-
"""probe3_restore v4 - S2 恢复算法验证（规格 §S2 probe3）。
v3 实测定位：第二次 New 不进录制态（rec=False）是 A 层空白的唯一根因——
首层 New 录制成功，但 B 归零+关眼后第二层 New 不录制，A 层无内容。
v4：Part1 录制触发矩阵——V0 控制轮（无 B，验证本会话 rec 读取可用）
    + V1(B@0闭眼) + V2(B@0开眼) + V3(B@1开眼)，每轮 New 后延迟读 rec
    （0s/0.2s/0.5s，排除"读滞后"假象），返回首个能触发录制的 (前置, 延迟)；
Part2：用胜出 (前置, 延迟) 跑完整恢复。V1/V2 下 B 归零（网格=base），A 应录得
    干净 dA，验证全强度网格 = base+dA+dB、层序（顶置 0 剩 base+dB）、强度写读往返；
    V3 下 B@1（网格=base+dB），A 内容可能被污染（录 dA-dB）或仍干净（录 dA），
    同时报告两个候选残差：全强度期望 = base+dA（污染）或 base+dA+dB（干净）。
运行：ZBrush 2026.1 ZScript 面板 → Python Scripting → Load 加载本文件。
前置：活动子工具任意状态（脚本自动 Tool:Import base.goz 重置）。"""
import os
import sys
import time

print("probe3 v4 loading...")
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


def _fresh_base():
    """重置：Tool:Import base.goz（替换当前 Tool，图层清零）。"""
    zbc.set_next_filename(f"{OUT_DIR}/base.goz".replace("\\", "/"))
    zbc.press("Tool:Import")
    time.sleep(0.3)


def _press_new_read_rec(delays=(0.0, 0.2, 0.5)):
    """Press New -> 按延迟序列读 rec 位。返回 [(delay, rec), ...]。"""
    zbc.press("Tool:Layers:New")
    out = []
    for d in delays:
        if d > 0:
            time.sleep(d)
        try:
            rec = zb.layer_recording(zbc)
        except Exception as e:
            rec = f"ERR:{type(e).__name__}"
        out.append((d, rec))
    return out


def _record_import_delayed(goz_path, rec_delay):
    """New -> 等 rec_delay 再读 rec -> 导入 goz_path -> 退录制。
    与 zbridge_085.layer_record_import 相同，仅多了延迟读，用于 A 层（第二次 New）。"""
    zb.layer_log_state(zbc, "rec_impD:before")
    zbc.press("Tool:Layers:New")
    if rec_delay > 0:
        time.sleep(rec_delay)
    zb.layer_log_state(zbc, "rec_impD:after_New")
    if not zb.layer_recording(zbc):
        zb.log("LAYER", "[FAIL] New 未进入录制态（延迟读 rec）")
        return False, "new_not_recording"
    zbc.set_next_filename(goz_path.replace("\\", "/"))
    zbc.press("Tool:Import")
    zb.layer_log_state(zbc, "rec_impD:after_Import")
    if zb.layer_recording(zbc):
        p = zb.layer_full_path(zbc)
        zbc.click(p, zbc.get_width(p) - 25, zbc.get_height(p) / 2)
        zb.layer_log_state(zbc, "rec_impD:after_exit_click")
    return True, ""


def _matrix():
    """Part1：录制触发矩阵。返回 (win_tag, win_delay, results dict)。"""
    zb.log("MATRIX", "--- Part1: New 录制触发矩阵 ---")
    results = {}

    # V0 控制轮：无层 New 应必录（probe2/v3 已验证），验证本会话 rec 读取可用
    _fresh_base()
    recs0 = _press_new_read_rec()
    results["V0_noB"] = [r[1] for r in recs0]
    zb.log("MATRIX", f"V0_noB (控制轮): rec 读数={recs0}")
    if not any(r[1] is True for r in recs0):
        zb.log("MATRIX", "[FAIL] V0 控制轮即不录制：rec 读取或 New 行为异常，中止矩阵")
        return None, None, results

    def _prep_V1():  # B@0 + 眼关（v3 失败前置）
        zb.layer_set_intensity(zbc, 0.0)

    def _prep_V2():  # B@0 + 眼开（网格仍=base）
        zb.layer_set_intensity(zbc, 0.0)
        zb.layer_set_visible(zbc, True)

    def _prep_V3():  # B@1 + 眼开（网格=base+dB）
        zb.layer_set_intensity(zbc, 1.0)
        zb.layer_set_visible(zbc, True)

    preps = [("V1_B0_eyeClosed", _prep_V1),
             ("V2_B0_eyeOpen", _prep_V2),
             ("V3_B1_eyeOpen", _prep_V3)]
    for tag, prep in preps:
        _fresh_base()
        ok, e = zb.layer_record_import(zbc, f"{OUT_DIR}/L1.goz")
        if not ok:
            zb.log("MATRIX", f"[FAIL] {tag}: B 层构建失败 {e}；跳过本轮")
            results[tag] = "B_build_fail"
            continue
        prep()
        zb.layer_log_state(zbc, f"{tag}: pre-New")
        recs = _press_new_read_rec()
        results[tag] = [r[1] for r in recs]
        hit = any(r[1] is True for r in recs)
        zb.log("MATRIX", f"{tag}: rec 读数={recs} -> {'录制' if hit else '不录制'}")
        if hit:
            win_delay = next(d for d, r in recs if r is True)
            zb.log("MATRIX", f"[PASS] {tag} 触发 New 录制（首个延迟={win_delay}s），胜出前置={tag}")
            return tag, win_delay, results
    zb.log("MATRIX", "[FAIL] V1/V2/V3 均未触发 New 录制")
    return None, None, results


def _full_restore(win_tag, win_delay):
    """Part2：用胜出 (前置, 延迟) 跑完整恢复验证。"""
    zb.log("RST", f"--- Part2: full restore (win={win_tag}, delay={win_delay}) ---")
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

    _fresh_base()
    n0 = zb.layer_detect(zbc)
    zb.log_pass("RST", n0 == 0, f"前置：活动子工具应无图层（实际 {n0}）")
    if n0 != 0:
        return
    # 1) 先建 LayerB（栈底）
    ok1, e1 = zb.layer_record_import(zbc, f"{OUT_DIR}/L1.goz")
    zb.layer_log_state(zbc, f"built B ok={ok1} e={e1}")
    if not ok1:
        return
    # 2) 应用胜出前置
    if win_tag == "V1_B0_eyeClosed":
        zb.layer_set_intensity(zbc, 0.0)
    elif win_tag == "V2_B0_eyeOpen":
        zb.layer_set_intensity(zbc, 0.0)
        zb.layer_set_visible(zbc, True)
    elif win_tag == "V3_B1_eyeOpen":
        zb.layer_set_intensity(zbc, 1.0)
        zb.layer_set_visible(zbc, True)
    zb.layer_log_state(zbc, f"after prep {win_tag}")
    # 3) 再建 LayerA（栈顶，延迟读 rec）
    ok2, e2 = _record_import_delayed(f"{OUT_DIR}/L0.goz", win_delay)
    zb.layer_log_state(zbc, f"built A ok={ok2} e={e2}")
    if not ok2:
        zb.log("RST", "[FAIL] A 层仍未进入录制态；跳过后续验证")
        return
    n = zb.layer_detect(zbc)
    zb.log_pass("RST", n == 2, f"层数应=2，实际 {n}")
    if n != 2:
        return
    # 4) 恢复 LayerB：导航下移（应到 B）-> 强度1 -> 开眼
    zb.layer_step(zbc, down=True)
    zb.layer_log_state(zbc, "after step down (应=B)")
    zb.layer_set_intensity(zbc, 1.0)
    zb.layer_set_visible(zbc, True)
    zb.layer_log_state(zbc, "after restore B")
    # 5) 全强度网格验证（期望按 win_tag 区分）
    zb.layer_goto_top(zbc, n)
    zb.layer_log_state(zbc, "after goto top")
    zb.export_goz(zbc, f"{OUT_DIR}/restore_full.goz")
    full = gozlib.read_goz_points(f"{OUT_DIR}/restore_full.goz")[1]
    if win_tag == "V3_B1_eyeOpen":
        # B@1 时 New：A 录制起点=base+dB，内容可能=dA-dB（污染），全强度=base+dA
        expect_full = gozlib.add_pts(base, dA)
        cand2 = gozlib.add_pts(gozlib.add_pts(base, dA), dB)
        r_cand2 = gozlib.residual_max(full, cand2)
        zb.log("RST", f"V3 候选 base+dA+dB residual={r_cand2:.6f}（若很小则 A 内容=干净 dA）")
    else:
        expect_full = gozlib.add_pts(gozlib.add_pts(base, dA), dB)
    resid = gozlib.residual_max(full, expect_full)
    zb.log("RST", f"full-stack residual={resid:.6f} (count={len(full)})")
    tol = max(gozlib.delta_norm(expect_full) * 1e-3, 1e-4)
    zb.log_pass("RST", len(full) == len(base) and resid <= tol,
                f"全强度网格 = 期望（win={win_tag}）")
    # 6) 层序交叉：此刻在栈顶（应=A），置顶 0 -> 剩 base+dB（New 插栈顶成立）
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


def run():
    try:
        zb.log_init("s3_restore")
        win_tag, win_delay, results = _matrix()
        zb.log("MATRIX", f"matrix results: {results}")
        if win_tag:
            _full_restore(win_tag, win_delay)
        else:
            zb.log("RST", "无可用胜出前置，跳过 Part2")
    except Exception as e:
        _fatal(e)


if __name__ == "__main__":
    run()
