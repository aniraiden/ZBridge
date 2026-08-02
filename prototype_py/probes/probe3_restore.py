# -*- coding: utf-8 -*-
"""probe3_restore v6 - S2 恢复算法验证（规格 §S2 probe3）。
v5 结论（同名层陷阱，根因分析完毕）：
  两层默认名相同（UI 显示 "Untitled Layer 1/0"，但 IGetTitle 对两层均返回
  "Untitled Layer"），按名寻址 Tool:Layers:Untitled Layer **恒命中首匹配 = 调色板
  列表第一行（栈顶）**。v5 全部 W-25 退录制点击、W-5 开眼点击、get_mod 读全部落在
  第一层（B）；第二层（A）录制从未退出、眼从未打开 → 三网格只有 base+dB。
  用户观察 "第二层形状=LayerA" 证实 A 内容其实录进了层（Import 作用于当前层，不走
  名称路径），只是从未被"激活"参与网格合成。
v6 方案：**不依赖命名，用 MoveUp/MoveDown 重排 + 首匹配寻址**（复用 v5 实测规律）：
  1. 建 B（唯一层，首匹配=B）→ W-25 退录制 ✓（v5 已证明该步正确）
  2. 归零 B（滑杆，当前层=B）
  3. 建 A（New 插栈底）→ MoveUp 把 A 移到栈顶 → 首匹配=A → 退录制 + 开眼舞步 ✓
  4. 需要 B 时再 SelectDown→MoveUp 把 B 移到栈顶
  - 强度全部走滑杆（当前层，选择式寻址，重名免疫）
  - 开眼用确定性舞步：置 0（自动关眼）→ IClick W-5（开眼+选中该行）→ 恢复强度
  - 每次导出在脚本内做残差分类（base / base+dA / base+dB / base+dA+dB），
    日志自包含，无需外部 analyze；任何寻址失效都会在分类里现形（自诊断）。
验证点：a_diag=base+dA / restore_full=base+dA+dB / restore_top0=base+dB /
层数 / 强度写读往返。
运行：ZBrush 2026.1 ZScript 面板 -> Python Scripting -> Load 加载本文件。
前置：活动子工具任意状态（脚本自动清理图层并导入 base.goz 重置）。"""
import os
import sys
import time

print("probe3 v6 loading...")
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
    策略：①直接导入；②逐层 Delete 清栈（杀掉录制态）后导入；③当前层 W-25 退录制后导入。"""
    for step in ("direct", "delete", "w25"):
        if step == "delete":
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


def _layer_import(goz_path, tag, exit_rec=True):
    """New -> 导入 goz_path -> [W-25 退录制]。
    exit_rec=False：新层在栈底暂不可寻址（首匹配=栈顶），退录制延后到 MoveUp 之后。
    不做 rec 读门（New 必录制）。层存活验证：New 后层数>0、Import 后层数不变。"""
    zb.layer_log_state(zbc, f"{tag}:before")
    zbc.press("Tool:Layers:New")
    zb.layer_log_state(zbc, f"{tag}:after_New")
    if zb.layer_detect(zbc) == 0:
        zb.log("LAYER", f"[FAIL] {tag}: New 后层数=0，中止")
        return False, "new_noop"
    zbc.set_next_filename(goz_path.replace("\\", "/"))
    zbc.press("Tool:Import")
    time.sleep(0.2)
    zb.layer_log_state(zbc, f"{tag}:after_Import")
    if zb.layer_detect(zbc) == 0:
        zb.log("LAYER", f"[FAIL] {tag}: Import 后层数=0（工具被替换），中止")
        return False, "tool_replaced"
    if exit_rec:
        try:
            p = zb.layer_full_path(zbc)
            zbc.click(p, zbc.get_width(p) - 25, zbc.get_height(p) / 2)
            zb.layer_log_state(zbc, f"{tag}:after_exit_click")
        except Exception as e:
            zb.log("LAYER", f"{tag}:exit click fail {type(e).__name__}: {e}")
            return False, f"exit_click:{type(e).__name__}"
    return True, ""


def _move_top(tag):
    """把当前层移到栈顶（MoveUp；已在顶则 no-op），使首匹配=当前层。"""
    zbc.press("Tool:Layers:MoveUp")
    zb.layer_log_state(zbc, f"{tag}:after_MoveUp(当前层→栈顶)")


def _eye_force_on_current(tag):
    """确定性开眼（当前层已在栈顶=首匹配）：置 0（自动关眼）-> IClick W-5 开眼 -> 恢复强度。
    零读依赖（cur 仅作恢复值，读到异常取 1.0）。"""
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


def _classify(tag, mesh, base, dA, dB):
    """残差分类：网格=base/base+dA/base+dB/base+dA+dB 中的哪一种。返回 (名称, 残差)。"""
    cands = {
        "base": base,
        "base+dA": gozlib.add_pts(base, dA),
        "base+dB": gozlib.add_pts(base, dB),
        "base+dA+dB": gozlib.add_pts(gozlib.add_pts(base, dA), dB),
    }
    rows = sorted(((gozlib.residual_max(mesh, c), n) for n, c in cands.items()))
    resid, name = rows[0]  # rows[i] = (residual, name)；解包顺序勿反
    zb.log(tag, f"分类 {name}: resid={resid:.6f}（次近 {rows[1][0]:.6f} {rows[1][1]}）")
    return name, resid


def _assert_mesh(tag, path, expect_name, base, dA, dB):
    m = gozlib.read_goz_points(path)[1]
    if len(m) != len(base):
        zb.log_pass(tag, False, f"顶点数 {len(m)} != {len(base)}")
        return
    name, resid = _classify(tag, m, base, dA, dB)
    ok = name == expect_name
    zb.log_pass(tag, ok, f"{tag} 应={expect_name} 实测={name} resid={resid:.6f}")


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

    # 1) 建 B（栈唯一层）：New -> 导入 L1 -> W-25 退录制（首匹配=B，v5 已验证该步正确）
    ok1, e1 = _layer_import(f"{OUT_DIR}/L1.goz", "B", exit_rec=True)
    if not ok1:
        return
    n = zb.layer_detect(zbc)
    zb.log_pass("RST", n == 1, f"B 建层后层数应=1（实际 {n}）")

    # 2) 归零 B：网格回 base + 自动关眼
    zbc.set("Tool:Layers:Layer Intensity", 0.0)
    zb.layer_log_state(zbc, "after zero B")

    # 3) 建 A（New 插栈底，暂不退录制——此时首匹配=B）
    ok2, e2 = _layer_import(f"{OUT_DIR}/L0.goz", "A", exit_rec=False)
    if not ok2:
        return
    n = zb.layer_detect(zbc)
    zb.log_pass("RST", n == 2, f"A 建层后层数应=2（实际 {n}）")

    # 4) MoveUp A -> 栈顶 -> 首匹配=A -> 退录制 + 开眼舞步 -> a_diag 应=base+dA
    _move_top("A")
    try:
        p = zb.layer_full_path(zbc)
        zbc.click(p, zbc.get_width(p) - 25, zbc.get_height(p) / 2)
        zb.layer_log_state(zbc, "A:after_exit_click(栈顶)")
    except Exception as e:
        zb.log("LAYER", f"A:exit click fail {type(e).__name__}: {e}")
        return
    _eye_force_on_current("a_diag/A")
    zb.export_goz(zbc, f"{OUT_DIR}/a_diag.goz")
    _assert_mesh("a_diag", f"{OUT_DIR}/a_diag.goz", "base+dA", base, dA, dB)

    # 5) restore_full：当前=A(顶)。SelectDown->B -> MoveUp B(顶) -> B 开眼舞步 -> 导出应=base+dA+dB
    zb.layer_step(zbc, down=True)
    zb.layer_log_state(zbc, "after SelectDown (应=B)")
    _move_top("B")
    _eye_force_on_current("restore/B")
    zb.export_goz(zbc, f"{OUT_DIR}/restore_full.goz")
    _assert_mesh("restore_full", f"{OUT_DIR}/restore_full.goz", "base+dA+dB", base, dA, dB)

    # 6) restore_top0：当前=B(顶)。SelectDown->A(底) -> A 置 0 -> 导出应=base+dB
    zb.layer_step(zbc, down=True)
    zb.layer_log_state(zbc, "after SelectDown (应=A)")
    zbc.set("Tool:Layers:Layer Intensity", 0.0)
    zb.export_goz(zbc, f"{OUT_DIR}/restore_top0.goz")
    _assert_mesh("restore_top0", f"{OUT_DIR}/restore_top0.goz", "base+dB", base, dA, dB)

    # 7) MoveUp A 回顶 -> 强度写读往返（A）-> 最终状态日志
    _move_top("A")
    zbc.set("Tool:Layers:Layer Intensity", 0.5)
    readback = zb.layer_intensity(zbc)
    zb.log("RST", f"set A=0.5 read_back={readback}")
    zb.log_pass("RST", abs(readback - 0.5) < 1e-6, "强度写读往返（A）")
    zbc.set("Tool:Layers:Layer Intensity", 1.0)
    _eye_force_on_current("final/A")
    zb.layer_log_state(zbc, "final state")
    zb.log("RST", f"final 层数={zb.layer_detect(zbc)}")


def run():
    try:
        zb.log_init("s3_restore")
        _run()
    except Exception as e:
        _fatal(e)


if __name__ == "__main__":
    run()
