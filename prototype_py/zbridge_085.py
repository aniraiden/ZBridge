# -*- coding: utf-8 -*-
"""zbridge_085 - ZBrush 2026+ 图层导出/导入原型。
日志系统 + GoZ 导出辅助 + 图层 UI 辅助层。运行于 ZBrush Python。
红线：不用 subprocess/multiprocessing；不覆写 stdout/stderr stream handler。
命令签名以 zbrush.commands 为准，机制以 doc/zscript_python_reference.md §7 8.5 定案为准。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gozlib  # 纯 Python：期望网格计算/记录解析共用

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
ZBRIDGE_REV = "0.8.5-probe-v3"  # 每次运行日志会打印，用于确认跑的是磁盘当前代码
_log_fh = None
_log_name = ""


def log_init(tag="run"):
    """打开新日志文件 log/zb085_YYYYMMDD_HHMMSS_<tag>.log。返回绝对路径。"""
    global _log_fh, _log_name
    os.makedirs(LOG_DIR, exist_ok=True)
    _log_name = f"zb085_{time.strftime('%Y%m%d_%H%M%S')}_{tag}.log"
    _log_fh = open(os.path.join(LOG_DIR, _log_name), "w", encoding="utf-8")
    log("LOG", f"session start: {_log_name} rev={ZBRIDGE_REV}")
    return os.path.join(LOG_DIR, _log_name)


def log(module, msg):
    """写一行 [HH:MM:SS.mmm] [模块] msg，控制台同步。"""
    line = f"[{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d}] [{module:8s}] {msg}"
    print(line, flush=True)
    if _log_fh is not None:
        _log_fh.write(line + "\n")
        _log_fh.flush()


def log_pass(module, cond, msg):
    """自动断言：cond True 记 PASS，否则记 FAIL 并返回 False（调用方决定是否中止）。"""
    if cond:
        log(module, f"[PASS] {msg}")
    else:
        log(module, f"[FAIL] {msg}")
    return bool(cond)


def export_goz(zbc, path):
    """FileNameSetNext + Tool:Export。path 必须正斜杠（反斜杠 → 缩放 ~70%）。"""
    path = path.replace("\\", "/")
    log("EXPORT", f"goz={path}")
    zbc.set_next_filename(path)
    zbc.press("Tool:Export")


def layer_detect(zbc):
    """层数探测：先 IsEnabled(Layer Intensity)（空层列表禁用）再碰 Scrollbar。
    无图层返回 0（空列表碰 Scrollbar = 未定义行为闪退，禁止）。"""
    if not zbc.exists("Tool:Layers:Layer Intensity"):
        return 0
    if not zbc.is_enabled("Tool:Layers:Layer Intensity"):
        return 0
    if not zbc.exists("Tool:Layers:Layers Scrollbar"):
        return 0
    zbc.set("Tool:Layers:Layers Scrollbar", 0, 255)
    n = int(zbc.get_secondary("Tool:Layers:Layers Scrollbar")) + 1
    return n if n >= 1 else 0


def layer_goto_top(zbc, count):
    """SelectUp x(层数) 饱和到顶（计数法，重名免疫）。"""
    for _ in range(count):
        zbc.press("Tool:Layers:SelectUp")


def layer_step(zbc, down=True):
    """向下/向上移动一层（栈内 no-op，多按无害）。"""
    zbc.press("Tool:Layers:SelectDown" if down else "Tool:Layers:SelectUp")


def layer_name(zbc):
    """当前层名：IGetTitle(Layer Intensity)。"""
    return zbc.get_title("Tool:Layers:Layer Intensity")


def layer_full_path(zbc):
    """当前层 full path：IGetTitle(...,True)，供 get_mod/click/width/height。"""
    return zbc.get_title("Tool:Layers:Layer Intensity", True)


def layer_log_state(zbc, tag):
    """诊断：记录当前选中层的 name/int/vis/rec 四项状态。"""
    try:
        name = layer_name(zbc)
        inten = layer_intensity(zbc)
        vis = layer_visible(zbc)
        rec = layer_recording(zbc)
        log("LSTATE", f"{tag}: name={name} int={inten} vis={vis} rec={rec}")
    except Exception as e:
        log("LSTATE", f"{tag}: <read fail: {type(e).__name__}: {e}>")


def layer_intensity(zbc):
    """当前层强度（0-1 域，选择式寻址）。"""
    return float(zbc.get("Tool:Layers:Layer Intensity"))


def layer_set_intensity(zbc, value):
    """写当前层强度（0-1 域）。"""
    zbc.set("Tool:Layers:Layer Intensity", float(value))
    log("LAYER", f"set_intensity={value} name={layer_name(zbc)}")


def layer_visible(zbc):
    """可见性读：IModGet bit1（值2）。"""
    return (zbc.get_mod(layer_full_path(zbc)) & 2) == 2


def layer_recording(zbc):
    """录制位读：IModGet bit0（值1）。"""
    return (zbc.get_mod(layer_full_path(zbc)) & 1) == 1


def layer_set_visible(zbc, want):
    """可见性写：期望与当前不一致才 IClick(W-5,H/2) 切换一次；W/H 现读。
    注：点击后立即 IModGet 读取可能滞后（S1 实测），勿用作状态门。"""
    path = layer_full_path(zbc)
    if layer_visible(zbc) != want:
        w = zbc.get_width(path)
        h = zbc.get_height(path)
        zbc.click(path, w - 5, h / 2)
        log("LAYER", f"click_eye want={want}")


def layer_record_import(zbc, goz_path):
    """New（自动录制）-> 导入 goz_path -> 退录制。返回 (ok, 异常消息)。
    全程记录录制位：New 前后/导入后/退出点击后，用于定位录制态异常。"""
    layer_log_state(zbc, "rec_import:before")
    zbc.press("Tool:Layers:New")
    layer_log_state(zbc, "rec_import:after_New")
    if not layer_recording(zbc):
        log("LAYER", "[FAIL] New 未进入录制态")
        return False, "new_not_recording"
    zbc.set_next_filename(goz_path.replace("\\", "/"))
    zbc.press("Tool:Import")
    layer_log_state(zbc, "rec_import:after_Import")
    if layer_recording(zbc):
        p = layer_full_path(zbc)
        zbc.click(p, zbc.get_width(p) - 25, zbc.get_height(p) / 2)
        layer_log_state(zbc, "rec_import:after_exit_click")
    return True, ""


# ======================= Task 6 全功能 export/import（S3） =======================


def subtool_name(zbc):
    """当前子工具名：IGetTitle(Tool:Item Info) 去掉末尾 2 字符（与主程序 manifest 命名一致）。"""
    t = zbc.get_title("Tool:Item Info")
    return t[:-2] if len(t) > 2 else t


def layer_clear(zbc):
    """归零后逐层 Delete 清空图层栈（保网格不变）。返回 (ok, 剩余层数)。"""
    try:
        n = layer_detect(zbc)
        if n == 0:
            return True, 0
        layer_goto_top(zbc, n)
        for i in range(n):
            layer_set_intensity(zbc, 0.0)
            if i < n - 1:
                layer_step(zbc, down=True)
        for _ in range(n + 2):
            zbc.press("Tool:Layers:Delete")
        remain = layer_detect(zbc)
        return (remain == 0), remain
    except Exception as e:
        log("CLR", f"layer_clear fail {type(e).__name__}: {e}")
        return False, -1


def layer_build_snapshot(zbc, goz_path, existing_count, want_vis):
    """建层步：New(自动录制) -> 导入 -> MoveUp×existing_count 到栈顶 -> W-25 退录制
    -> 置0（确定性关眼）-> want_vis 时 IClick 开眼（此时本层=栈顶，按名寻址唯一安全）
    -> **强度保持 0**（录制隔离：后续层 New 的录制起点=基准网格，若这里设了目标强度，
    可见层会污染后建层的录制起点，delta 变成 dA−dB——2026-08-03 实测）。
    强度由 import_layers 的恢复 pass 统一设置（MoveUp 到栈顶机制）。
    层存活用 IsEnabled 判断（rec 读不可靠，不做读门）。返回 (ok, err)。"""
    zbc.press("Tool:Layers:New")
    if not zbc.is_enabled("Tool:Layers:Layer Intensity"):
        return False, "new_noop"
    zbc.set_next_filename(goz_path.replace("\\", "/"))
    zbc.press("Tool:Import")
    time.sleep(0.2)
    if not zbc.is_enabled("Tool:Layers:Layer Intensity"):
        return False, "tool_replaced"
    for _ in range(existing_count):
        zbc.press("Tool:Layers:MoveUp")
    try:
        p = layer_full_path(zbc)
        zbc.click(p, zbc.get_width(p) - 25, zbc.get_height(p) / 2)
    except Exception as e:
        return False, f"exit_click:{type(e).__name__}"
    # 可见性设置（本层=栈顶=首匹配，按名寻址安全）；强度保持 0
    try:
        zbc.set("Tool:Layers:Layer Intensity", 0.0)
        if want_vis:
            p = layer_full_path(zbc)
            zbc.click(p, zbc.get_width(p) - 5, zbc.get_height(p) / 2)  # 关->开
            time.sleep(0.05)
    except Exception as e:
        return False, f"state_set:{type(e).__name__}"
    return True, ""


def write_layers_txt(path, recs):
    """写 layers.txt：每条 "<subtool>|<idx>|<name>|<intensity>|<visible>|0|0" + '\\0'
    （null-terminated records，与主程序 0.8.0 一致；enabled/vertexCount 原型填 0）。"""
    data = "".join(
        f"{r['subtool']}|{r['idx']}|{r['name']}|{float(r['intensity']):g}|{1 if r['visible'] else 0}|0|0\x00"
        for r in recs
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
    log("EXP", f"wrote {path} ({len(recs)} recs, {len(data)} bytes)")


def read_layers_txt(path):
    """解析 layers.txt（null-terminated records，7 字段）。返回 dict 列表。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    recs = []
    for rec in raw.split("\x00"):
        fields = rec.split("|")
        if len(fields) < 5 or not fields[1].strip():
            continue
        try:
            recs.append({
                "subtool": fields[0],
                "idx": int(fields[1]),
                "name": fields[2],
                "intensity": float(fields[3]),
                "visible": int(fields[4]) != 0,
            })
        except (ValueError, IndexError):
            continue
    return recs


def expected_mesh(out_dir, subtool, recs, vis_blocks=True):
    """期望网格 = LayerBase + Σ (vis_blocks 且不可见 ? 0 : intensity) × delta_i。
    delta_i = Layer<i> - LayerBase；缺任一文件返回 None。"""
    out_dir = out_dir.replace("\\", "/")
    base_path = f"{out_dir}/{subtool}_LayerBase.goz"
    if not os.path.exists(base_path):
        return None
    base = gozlib.read_goz_points(base_path)[1]
    pts = list(base)
    for r in recs:
        p = f"{out_dir}/{subtool}_Layer{r['idx']}.goz"
        if not os.path.exists(p):
            return None
        d = gozlib.vertex_delta(base, gozlib.read_goz_points(p)[1])
        if r["visible"] or not vis_blocks:
            pts = gozlib.add_pts(pts, gozlib.add_scaled(d, float(r["intensity"])))
    return pts


def _sdiv_switch_max(zbc):
    """切到最高细分级别（快照均在最高 SDiv 导出，顶点一一对齐）。返回原 SDiv 或 None。"""
    try:
        if not zbc.exists("Tool:Geometry:SDiv") or not zbc.is_enabled("Tool:Geometry:SDiv"):
            return None
        cur = float(zbc.get("Tool:Geometry:SDiv"))
        mx = float(zbc.get_max("Tool:Geometry:SDiv"))
        if mx > 0:
            zbc.set("Tool:Geometry:SDiv", mx)
            log("SDIV", f"switch {cur} -> max {mx}")
        return cur
    except Exception as e:
        log("SDIV", f"switch_max fail {type(e).__name__}: {e}")
        return None


def _sdiv_restore(zbc, cur):
    if cur is None:
        return
    try:
        zbc.set("Tool:Geometry:SDiv", cur)
        log("SDIV", f"restore -> {cur}")
    except Exception as e:
        log("SDIV", f"restore fail {type(e).__name__}: {e}")


def export_layers(zbc, out_dir, subtool_name):
    """导出活动子工具全部图层（T3 流程 + 导出后恢复原状态）。
    文件：<out_dir>/<subtool_name>_LayerBase.goz、_Layer<i>.goz、layers.txt
    返回记录数；无图层返回 0。"""
    n = layer_detect(zbc)
    log("EXP", f"subtool={subtool_name} layers={n}")
    if n == 0:
        return 0
    out_dir = out_dir.replace("\\", "/")
    os.makedirs(out_dir, exist_ok=True)
    # 1. 记录各层原状态（栈顶->栈底；layerIndex = n-1-pos，0=原始栈底层）
    recs = []
    layer_goto_top(zbc, n)
    for i in range(n):
        recs.append({
            "subtool": subtool_name,
            "idx": n - 1 - i,
            "name": layer_name(zbc),
            "intensity": layer_intensity(zbc),
            "visible": 1 if layer_visible(zbc) else 0,
        })
        if i < n - 1:
            layer_step(zbc, down=True)
    for r in recs:
        log("EXP", f"rec idx={r['idx']} name={r['name']} int={r['intensity']} vis={r['visible']}")
    # 2. 全部归零 -> 导出基准网格
    layer_goto_top(zbc, n)
    for i in range(n):
        layer_set_intensity(zbc, 0.0)
        if i < n - 1:
            layer_step(zbc, down=True)
    export_goz(zbc, f"{out_dir}/{subtool_name}_LayerBase.goz")
    # 3. 逐层快照（当前在栈底=layerIndex0；向上逐层；j 即 layerIndex）
    for j in range(n):
        layer_set_visible(zbc, True)      # 开眼（可见关阻断形变，先开眼）
        layer_set_intensity(zbc, 1.0)
        export_goz(zbc, f"{out_dir}/{subtool_name}_Layer{j}.goz")
        layer_set_intensity(zbc, 0.0)     # 置0防残留+自动关眼
        if j < n - 1:
            layer_step(zbc, down=False)   # SelectUp
    # 4. 写 layers.txt
    write_layers_txt(f"{out_dir}/layers.txt", recs)
    # 5. 恢复原状态（当前=栈顶；recs 顺序=栈顶->栈底；先强度后可见性，对称恢复）
    for j, r in enumerate(recs):
        if j > 0:
            layer_step(zbc, down=True)
        layer_set_intensity(zbc, r["intensity"])
        layer_set_visible(zbc, bool(r["visible"]))
    log("EXP", f"export done n={n}")
    return n


def import_layers(zbc, out_dir, subtool_name=None):
    """重建活动子工具图层栈（T4 顺序 + v6 MoveUp/首匹配机制）。
    读取 <out_dir>/layers.txt；subtool_name 为 None 时导入全部记录。
    前置：活动子工具 = 干净网格（导入即录制，录制起点须为零网格）。
    流程：清空现有图层 -> 切最高 SDiv -> 按 layerIndex 升序逐层录制导入
    （New -> Import -> MoveUp×k 到顶 -> W-25 退录制 -> 可见性 -> 置0）
    -> 恢复每层强度（滑杆，栈顶->栈底）-> 切回原 SDiv。
    返回 (重建层数, 失败数)。"""
    out_dir = out_dir.replace("\\", "/")
    path = f"{out_dir}/layers.txt"
    if not os.path.exists(path):
        log("IMP", f"[FAIL] 缺失 {path}")
        return 0, 1
    recs = read_layers_txt(path)
    if subtool_name is not None:
        recs = [r for r in recs if r["subtool"] == subtool_name]
    recs.sort(key=lambda r: r["idx"])
    log("IMP", f"records={len(recs)} subtool={subtool_name or 'ALL'}")
    if not recs:
        log("IMP", "[FAIL] 无匹配记录")
        return 0, 1
    ok, remain = layer_clear(zbc)
    if not ok:
        log("IMP", f"[FAIL] 图层清空失败（剩余 {remain}）")
        return 0, remain
    cur_sdiv = _sdiv_switch_max(zbc)
    built_recs = []
    fails = 0
    for r in recs:
        goz = f"{out_dir}/{r['subtool']}_Layer{r['idx']}.goz"
        if not os.path.exists(goz):
            log("IMP", f"[FAIL] 缺失 {goz}（idx={r['idx']}）")
            fails += 1
            continue
        ok2, err = layer_build_snapshot(zbc, goz, len(built_recs), bool(r["visible"]))
        if not ok2:
            log("IMP", f"[FAIL] 建层 idx={r['idx']} 失败: {err}")
            fails += 1
            continue
        log("IMP", f"built idx={r['idx']} name={r['name']} int={r['intensity']} vis={r['visible']}")
        built_recs.append(r)
    # 恢复强度+可见性：重名层按名寻址恒命中栈顶，故每层先导航到栈底再 MoveUp 到栈顶
    # 后操作（首匹配=本层）；从 idx 最小开始，处理完保留在栈顶，层序自然复原为记录序。
    if built_recs:
        for j, r in enumerate(built_recs):
            for _ in range(len(built_recs) - 1):
                layer_step(zbc, down=True)  # 到栈底（未处理的最下层）
            for _ in range(len(built_recs) - 1):
                zbc.press("Tool:Layers:MoveUp")  # 移到栈顶
            layer_set_intensity(zbc, r["intensity"])
            layer_set_visible(zbc, bool(r["visible"]))
    _sdiv_restore(zbc, cur_sdiv)
    n = layer_detect(zbc)
    log("IMP", f"built={len(built_recs)} fails={fails} final_layer_count={n}")
    return len(built_recs), fails
