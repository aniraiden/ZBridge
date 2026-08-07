# -*- coding: utf-8 -*-
"""probe_rename - 探测 ZBrush 2026 Python 中图层重命名机制（层名恢复的前置验证）。
前置：当前子工具至少有 1 个图层。
方式：FileNameSetNext(目标名) + Tool:Layers:Rename，读回层名确认是否生效。
若 press Rename 弹出模态命名框或挂起，属预期风险，请如实反馈（卡在哪一步/弹了什么窗）。
输出：log/zb085_*_probe_rename.log"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _m in ("gozlib", "zbridge_085"):
    sys.modules.pop(_m, None)
import zbridge_085 as zb
from zbrush import commands as zbc


def run():
    zb.log_init("probe_rename")
    n = zb.layer_detect(zbc)
    if n == 0:
        zb.log("REN", "[FAIL] 无图层：请先在当前子工具上创建至少一个图层后重跑")
        return
    zb.layer_goto_top(zbc, n)
    zb.layer_log_state(zbc, "before")
    try:
        zb.log("REN", f"exists(Tool:Layers:Rename)={zbc.exists('Tool:Layers:Rename')}")
        zb.log("REN", f"enabled(Tool:Layers:Rename)={zbc.is_enabled('Tool:Layers:Rename')}")
    except Exception as e:
        zb.log("REN", f"diag fail {type(e).__name__}: {e}")
    ok, err = zb.layer_rename(zbc, "RenameProbe")
    zb.log("REN", f"rename_attempt ok={ok} err={err}")
    zb.layer_log_state(zbc, "after_rename")
    got = zb.layer_name(zbc)
    zb.log_pass("REN", got == "RenameProbe", f"层名=目标名？got={got}")
    if got == "RenameProbe":
        zb.layer_rename(zbc, "Untitled Layer")  # 改回默认名（失败无妨，用户可手动改）
    zb.log("REN", "PROBE_DONE")


run()
