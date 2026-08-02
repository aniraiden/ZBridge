# -*- coding: utf-8 -*-
"""zbridge_085 - ZBrush 2026+ 图层导出/导入原型。
日志系统 + GoZ 导出辅助 + 图层 UI 辅助层。运行于 ZBrush Python。
红线：不用 subprocess/multiprocessing；不覆写 stdout/stderr stream handler。
命令签名以 zbrush.commands 为准，机制以 doc/zscript_python_reference.md §7 8.5 定案为准。"""
import os
import sys
import time

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
ZBRIDGE_REV = "0.8.5-probe-v2"  # 每次运行日志会打印，用于确认跑的是磁盘当前代码
_log_fh = None
_log_name = ""


def fresh():
    """强制刷新 gozlib 与自身：ZBrush Python 解释器跨 Load 持久，`import` 只首次真执行，
    不刷新会复用旧版模块（S1 曾导致 tag=10000 旧 gozlib 污染 probe2/3 指标）。
    每个探测脚本 run() 开头必须调用一次。"""
    import importlib
    import gozlib
    importlib.reload(gozlib)
    importlib.reload(sys.modules[__name__])


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
