# -*- coding: utf-8 -*-
"""S3 e2e 第一段：导出。直接 Load 即执行（无需改任何配置）。
前置：当前子工具含 2 个图层（建议命名 LayerA/LayerB，形状互异；名字唯一才安全）。
脚本会强制设定确定性状态（栈底层@1.0 显示 / 栈顶层@1.0 隐藏）后执行 export_layers，
并在脚本内自检快照隔离性与 layers.txt。
输出：log/zb085_*_s3_e2e_export.log + out/<subtool>_LayerBase/0/1.goz + layers.txt"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.dirname(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
# 强制真重新导入（ZBrush 解释器跨 Load 缓存旧模块）
for _m in ("probe_e2e", "gozlib", "zbridge_085"):
    sys.modules.pop(_m, None)
import probe_e2e

try:
    probe_e2e.run_export()
except Exception as e:
    probe_e2e._fatal(e)
