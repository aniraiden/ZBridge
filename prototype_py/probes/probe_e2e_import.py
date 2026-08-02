# -*- coding: utf-8 -*-
"""S3 e2e 第二段：导入。直接 Load 即执行（无需改任何配置）。
前置：新会话导入 out/<subtool>_LayerBase.goz 得到干净网格后 Load 本文件。
执行 import_layers（全部记录）-> 导出 e2e_final.goz 与期望网格比对 -> VERIFIED 报告。
输出：log/zb085_*_s3_e2e_import.log（末尾 VERIFIED=PASS/CHECK/FAIL）"""
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
    probe_e2e.run_import()
except Exception as e:
    probe_e2e._fatal(e)
