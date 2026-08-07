# -*- coding: utf-8 -*-
"""probe_reconstruct_sdiv - 重建细分级别探测（新会话导入 LayerBase.goz 后运行）。
背景：导入 goz（无细分级别）后，录制导入各层 goz 会因顶点数不匹配而替换工具。
方案：用 Reconstruct Subdiv 从最高级网格反推创建低级别（最高级顶点数不变，
    与各层 goz 顶点一致）-> 录制导入顶点匹配 -> 不替换工具，且细分级别恢复。
本脚本：反复按 Reconstruct Subdiv 直到 SDiv max 达到目标级别（默认 3），
    记录每步 max 变化以验证"级别增加、顶点数不变"（顶点数由 ZBrush 保证）。
运行：新会话 -> Tool:Import 导入 out/<subtool>_LayerBase.goz -> Load 本文件。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _m in ("gozlib", "zbridge_085"):
    sys.modules.pop(_m, None)
import zbridge_085 as zb
from zbrush import commands as zbc

TARGET_LEVELS = 3  # 用户原始文件细分级别数；不同请改这里


def run():
    zb.log_init("reconstruct_sdiv")
    zb.log("REC", f"target levels={TARGET_LEVELS}")
    exists = zbc.exists("Tool:Geometry:Reconstruct Subdiv")
    enabled = zbc.is_enabled("Tool:Geometry:Reconstruct Subdiv")
    zb.log("REC", f"Reconstruct Subdiv exists={exists} enabled={enabled}")
    sdiv_avail = zbc.exists("Tool:Geometry:SDiv") and zbc.is_enabled("Tool:Geometry:SDiv")
    if not sdiv_avail:
        zb.log("REC", "SDiv 不可用（当前网格无细分级别）")
    else:
        cur = float(zbc.get("Tool:Geometry:SDiv"))
        mx = float(zbc.get_max("Tool:Geometry:SDiv"))
        zb.log("REC", f"sdiv before: cur={cur} max={mx}")
        for i in range(6):
            if not zbc.is_enabled("Tool:Geometry:Reconstruct Subdiv"):
                zb.log("REC", f"press {i + 1}: Reconstruct 不可用，停止")
                break
            zbc.press("Tool:Geometry:Reconstruct Subdiv")
            time.sleep(0.4)
            mx2 = float(zbc.get_max("Tool:Geometry:SDiv"))
            zb.log("REC", f"press {i + 1}: sdiv max={mx2}")
            if mx2 <= mx:
                zb.log("REC", "max 未增加——Reconstruct 无效果（拓扑不满足？），停止")
                break
            mx = mx2
            if mx >= TARGET_LEVELS:
                break
        cur2 = float(zbc.get("Tool:Geometry:SDiv"))
        zb.log("REC", f"sdiv after: cur={cur2} max={mx}")
        zb.log_pass("REC", mx >= TARGET_LEVELS, f"重建到 {mx} 级（目标 {TARGET_LEVELS}）")
    zb.log("REC", "下一步：切回最高 SDiv（SDiv 滑杆调到 max），再 Load probe_e2e3_import.py")
    zb.log("REC", "PROBE_DONE")


run()
