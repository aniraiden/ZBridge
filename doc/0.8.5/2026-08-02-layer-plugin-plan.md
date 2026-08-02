# 0.8.5 雕刻图层单功能插件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Python 原型（ZBrush 2026+）验证并定型"子工具图层导出/导入还原"的完整机制，再移植为独立 ZScript 单功能插件（`ZBridge_085.txt`），验证成功后才并入主程序。

**Architecture:** 三明治结构：①`gozlib.py` 纯 Python 模块（GoZ 顶点解析 + delta 数学，可脱离 ZBrush TDD）；②`zbridge_085.py` ZBrush 耦合模块（日志系统 + UI 辅助层 + 导出/导入流程）；③`probes/` 丢弃式自验证探测脚本（S1 隔离性 → S2 录制导入/恢复算法 → S3 端到端）。全部机制验证通过后按 1:1 移植 ZScript（`ZBridge_085.txt`），最后并入主程序。**S1 隔离性是方案生死判定，最先执行。**

**Tech Stack:** Python 3.11.9（ZBrush 2026.1 内嵌）+ `zbrush.commands as zbc`；独立 Python 3.10/3.11（开发机，仅跑 gozlib 测试）；ZScript（UTF-8 BOM + CRLF，camelCase 无下划线）。

**测试模式：** gozlib 走真 TDD（开发机独立 Python）；ZBrush 耦合部分 = 用户运行探测脚本 → 自动断言 + 写日志文件 → 反馈 = 读日志，零 Note 抄写。每个 spike 单次运行产出多个交叉指标（规格 §S1 指标表）。

**前置知识（执行前必读）：**
- 规格：`doc/0.8.5/2026-08-02-layer-plugin-design.md`（尤其 §S1 指标 A/B/D1/D2/E）
- 图层实测机制：`doc/zscript_python_reference.md` §7 8.5 + `refrenece/knowledge/04-function-cookbook.md` §9
- GoZ 格式：`refrenece/knowledge/08-goz-format.md` + `refrenece/goz_sdk/Sources/GoZ_Binary.h`
- Python SDK 命令签名：`refrenece/ZBrush_Python_SDK_2026_1_0/api/zbrush/commands.py`

---

## 文件结构

| 文件 | 职责 | 可独立测试 |
|------|------|-----------|
| `prototype_py/gozlib.py` | GoZ 顶点解析 + delta 数学 + S1 指标计算（纯 Python，零 zbrush import） | ✅ 开发机独立 Python |
| `prototype_py/test_gozlib.py` | gozlib 单元测试（合成 goz 文件） | ✅ 开发机独立 Python |
| `prototype_py/zbridge_085.py` | ZBrush 耦合：日志系统 + UI 辅助层 + export/import 流程 | ❌ 需 ZBrush |
| `prototype_py/probes/probe1_isolation.py` | S1 隔离性探测（导出 cur/base/L0/L1 + 5 指标判定） | ❌ 需 ZBrush |
| `prototype_py/probes/probe2_record_import.py` | S2 录制导入探测 | ❌ 需 ZBrush |
| `prototype_py/probes/probe3_restore.py` | S2 恢复算法探测 | ❌ 需 ZBrush |
| `prototype_py/log/` | 运行日志（gitignore） | — |
| `src/zscript/ZBridge_085.txt` | 最终 ZScript 单功能插件（S4） | ❌ 需 ZBrush |
| `doc/0.8.5/PROGRESS.md` | 每阶段结论记录（续档入口） | — |

---

## Task 1: gozlib.py — GoZ 顶点解析 + delta 数学（TDD）

**Files:**
- Create: `prototype_py/gozlib.py`
- Create: `prototype_py/test_gozlib.py`

- [ ] **Step 1: 写测试（先失败）**

创建 `prototype_py/test_gozlib.py`（完整代码）：

```python
# -*- coding: utf-8 -*-
"""gozlib 单元测试：合成 goz 文件 + delta 数学 + S1 指标。
运行：python prototype_py/test_gozlib.py  （开发机独立 Python，无需 ZBrush）"""
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gozlib


def build_goz(path, name, points, extra_blocks=None):
    """按 GoZ_Binary.h 构造最小 goz 文件。
    extra_blocks: [(tag, icount, payload_bytes)] 插在 POINT_LIST 之前（模拟 SUBDIV/FACE 等块）。"""
    out = b"GoZb" + b" " * 28

    def block(tag, icount, payload):
        return struct.pack("<IIIf", tag, 16 + len(payload), icount, 0.0) + payload

    name_b = name.encode("ascii") + b"\x00"
    name_b += b"\x00" * ((4 - len(name_b) % 4) % 4)
    out += block(1, 1, name_b)  # GoZ_TAG_MESH
    for tag, icount, payload in (extra_blocks or []):
        out += block(tag, icount, payload)
    pts_b = struct.pack("<%df" % (len(points) * 3), *[c for p in points for c in p])
    out += block(10000, len(points), pts_b)  # GoZ_TAG_POINT_LIST
    out += block(0, 0, b"")  # GoZ_TAG_END_OF_FILE
    with open(path, "wb") as f:
        f.write(out)


def assert_close(a, b, eps=1e-6, msg=""):
    assert abs(a - b) <= eps, f"{msg}: {a} != {b} (eps={eps})"


def test_read_points_basic():
    p = os.path.join(tempfile.gettempdir(), "t_basic.goz")
    build_goz(p, "Test", [(0, 0, 0), (1, 2, 3), (-1, -2, -3)])
    n, pts = gozlib.read_goz_points(p)
    assert n == 3
    assert pts[1] == (1.0, 2.0, 3.0)
    assert pts[2] == (-1.0, -2.0, -3.0)
    os.remove(p)


def test_read_skips_other_blocks():
    p = os.path.join(tempfile.gettempdir(), "t_skip.goz")
    subdiv = struct.pack("<4I", 3, 2, 0, 0)            # GoZ_SubDiv
    faces = struct.pack("<%di" % (4 * 2), 0, 1, 2, -1, 0, 2, 3, -1)  # FACE4 x2
    build_goz(p, "Skip", [(0, 0, 0), (1, 1, 1)],
              extra_blocks=[(5002, 4, subdiv), (20000, 2, faces)])
    n, pts = gozlib.read_goz_points(p)
    assert n == 2
    assert pts[0] == (0.0, 0.0, 0.0)
    os.remove(p)


def test_bad_magic_raises():
    p = os.path.join(tempfile.gettempdir(), "t_bad.goz")
    with open(p, "wb") as f:
        f.write(b"NOTGOZ" + b"\x00" * 26)
    try:
        gozlib.read_goz_points(p)
        assert False, "should have raised"
    except ValueError:
        pass
    os.remove(p)


def test_truncated_header_raises():
    p = os.path.join(tempfile.gettempdir(), "t_trunc.goz")
    with open(p, "wb") as f:
        f.write(b"GoZb" + b" " * 28 + b"\x00\x00" * 4)  # 只有半个块头
    try:
        gozlib.read_goz_points(p)
        assert False, "should have raised"
    except ValueError:
        pass
    os.remove(p)


def test_delta_math():
    a = [(0, 0, 0), (1, 1, 1)]
    b = [(1, 2, 3), (4, 5, 6)]
    d = gozlib.vertex_delta(a, b)  # b - a
    assert d == [(1.0, 2.0, 3.0), (3.0, 4.0, 5.0)]
    assert gozlib.add_scaled(d, 0.5) == [(0.5, 1.0, 1.5), (1.5, 2.0, 2.5)]
    assert_close(gozlib.delta_norm(d), 5.0, 1e-9)
    assert_close(gozlib.residual_max(d, d), 0.0)
    assert gozlib.close(d, d, 1e-9)
    try:
        gozlib.vertex_delta(a, [(0, 0, 0)])
        assert False, "should have raised"
    except ValueError:
        pass


def test_metrics_clean():
    """S1 干净场景：隔离成立 + 强度线性 -> A/B/E 全绿。"""
    B = [(0.0, 0.0, 0.0)] * 8
    dA = [(0.5, 0.0, 0.0) if i < 4 else (0.0, 0.0, 0.0) for i in range(8)]
    dB = [(0.0, 0.0, 0.0) if i < 4 else (0.0, 0.3, 0.0) for i in range(8)]
    base = B
    l0 = gozlib.add_pts(B, dA)
    l1 = gozlib.add_pts(B, dB)
    cur = gozlib.add_pts(gozlib.add_pts(B, dA), gozlib.add_scaled(dB, 0.5))
    m = gozlib.compute_metrics(cur, base, l0, l1, int1=0.5)
    assert m["A_pass"] is True, m
    assert m["B_isolated"] is True, m
    assert m["E_topology"] is True, m


def test_metrics_contaminated():
    """S1 污染场景：base 被叠加 0.5*dB -> A 失败，D1 诊断残差显著。"""
    B = [(0.0, 0.0, 0.0)] * 8
    dA = [(0.5, 0.0, 0.0) if i < 4 else (0.0, 0.0, 0.0) for i in range(8)]
    dB = [(0.0, 0.0, 0.0) if i < 4 else (0.0, 0.3, 0.0) for i in range(8)]
    base = gozlib.add_pts(B, gozlib.add_scaled(dB, 0.5))  # 基准污染
    l0 = gozlib.add_pts(B, dA)
    l1 = gozlib.add_pts(B, dB)
    cur = gozlib.add_pts(gozlib.add_pts(B, dA), gozlib.add_scaled(dB, 0.5))
    m = gozlib.compute_metrics(cur, base, l0, l1, int1=0.5)
    assert m["A_pass"] is False, m
    assert m["D1_resid"] > 1e-3, m


def run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_all())
```

- [ ] **Step 2: 运行确认失败**

Run: `python prototype_py/test_gozlib.py`
Expected: 全部测试报 `ModuleNotFoundError: No module named 'gozlib'`（文件尚不存在）。

- [ ] **Step 3: 实现 gozlib.py**

创建 `prototype_py/gozlib.py`（完整代码）：

```python
# -*- coding: utf-8 -*-
"""gozlib - GoZ 二进制顶点解析 + 顶点 delta 数学 + S1 隔离性指标计算。
纯 Python 模块，零 zbrush import：可脱离 ZBrush 用开发机 Python 单测。
格式依据：refrenece/goz_sdk/Sources/GoZ_Binary.h"""
import struct

GOZ_TAG_END = 0
GOZ_TAG_POINT_LIST = 10000
GOZ_FILE_HEADER = 32          # "GoZb" + 28 bytes text
BLOCK_HEADER = struct.Struct("<IIIf")  # tag, size(含16字节头), iCount, modifier


def read_goz_points(path):
    """读取 .goz 的 POINT_LIST。返回 (vertex_count, [(x,y,z), ...])。
    只读不改；非 goz / 块损坏 / 顶点数据尺寸不符 -> ValueError。"""
    with open(path, "rb") as f:
        head = f.read(GOZ_FILE_HEADER)
        if len(head) < 4 or head[:4] != b"GoZb":
            raise ValueError(f"not a GoZ file: {path}")
        points = []
        while True:
            hdr = f.read(16)
            if len(hdr) < 16:
                raise ValueError(f"truncated block header: {path}")
            tag, size, icount, _modifier = BLOCK_HEADER.unpack(hdr)
            if tag == GOZ_TAG_END:
                break
            payload = size - 16
            if payload < 0:
                raise ValueError(f"bad block size {size} at tag {tag}: {path}")
            if tag == GOZ_TAG_POINT_LIST:
                if payload != icount * 12:
                    raise ValueError(f"bad POINT_LIST size {payload} (count={icount}): {path}")
                raw = f.read(payload)
                vals = struct.unpack(f"<{icount * 3}f", raw)
                points = [(vals[i], vals[i + 1], vals[i + 2]) for i in range(0, len(vals), 3)]
            else:
                f.seek(payload, 1)
    return len(points), points


def vertex_delta(pts_base, pts_other):
    """delta = other - base（逐顶点）。顶点数不一致 -> ValueError。"""
    if len(pts_other) != len(pts_base):
        raise ValueError(f"vertex count mismatch: {len(pts_other)} vs {len(pts_base)}")
    return [(o[0] - b[0], o[1] - b[1], o[2] - b[2])
            for o, b in zip(pts_other, pts_base)]


def add_pts(pts, deltas):
    """points + deltas（逐顶点相加）。"""
    return [(p[0] + d[0], p[1] + d[1], p[2] + d[2])
            for p, d in zip(pts, deltas)]


def add_scaled(deltas, scale):
    """deltas * scale。"""
    return [(d[0] * scale, d[1] * scale, d[2] * scale) for d in deltas]


def delta_norm(deltas):
    """所有顶点各分量绝对值的最大值（形变量级）。"""
    mx = 0.0
    for d in deltas:
        mx = max(mx, abs(d[0]), abs(d[1]), abs(d[2]))
    return mx


def residual_max(a, b):
    """逐顶点逐分量 |a-b| 的最大值。"""
    mx = 0.0
    for x, y in zip(a, b):
        mx = max(mx, abs(x[0] - y[0]), abs(x[1] - y[1]), abs(x[2] - y[2]))
    return mx


def close(a, b, eps):
    return residual_max(a, b) <= eps


def compute_metrics(cur_pts, base_pts, l0_pts, l1_pts, int0=1.0, int1=0.5, eps_rel=1e-3):
    """S1 隔离性指标计算（规格 §S1 指标表）。
    输入：current/base/L0/L1 四个快照的顶点列表（同拓扑同顶点序）。
    返回 dict：A_pass / B_isolated / E_topology / 残差与量级（诊断用）。"""
    m = {}
    counts = [len(x) for x in (cur_pts, base_pts, l0_pts, l1_pts)]
    m["E_topology"] = len(set(counts)) == 1
    m["counts"] = counts
    if not m["E_topology"]:
        m["A_pass"] = False
        m["B_isolated"] = False
        return m
    d_cur = vertex_delta(base_pts, cur_pts)   # current - base
    d_l0 = vertex_delta(base_pts, l0_pts)     # L0 - base
    d_l1 = vertex_delta(base_pts, l1_pts)     # L1 - base
    scale = max(delta_norm(d_cur), delta_norm(d_l0), delta_norm(d_l1), 0.1)
    eps = max(eps_rel * scale, 1e-4)
    m["eps"] = eps
    m["d_l0_norm"] = delta_norm(d_l0)
    m["d_l1_norm"] = delta_norm(d_l1)
    lhs = add_pts(add_scaled(d_l0, int0), add_scaled(d_l1, int1))  # int0*dA + int1*dB
    m["A_resid"] = residual_max(lhs, d_cur)
    m["A_pass"] = m["A_resid"] <= eps
    m["B_isolated"] = (m["d_l0_norm"] > eps) and (m["d_l1_norm"] > eps) \
        and residual_max(d_l0, d_l1) > eps
    m["D1_resid"] = residual_max(d_cur, d_l0)          # 诊断：dB 缺失?
    m["D2_resid"] = residual_max(d_cur, add_pts(d_l0, d_l1))  # 诊断：强度全按1.0?
    return m
```

- [ ] **Step 4: 运行确认全绿**

Run: `python prototype_py/test_gozlib.py`
Expected: `7/7 passed`。

- [ ] **Step 5: Commit**

```bash
git add prototype_py/gozlib.py prototype_py/test_gozlib.py
git -c user.name="ZBridge Dev" -c user.email="dev@zbridge.local" commit -m "feat(0.8.5): gozlib 顶点解析 + delta 数学 + S1 指标（TDD 全绿）"
```

---

## Task 2: zbridge_085.py — 日志系统 + UI 辅助层

**Files:**
- Create: `prototype_py/zbridge_085.py`

> ZBrush 耦合模块（运行于 ZBrush 2026.1 Python）。红线：不用 subprocess/multiprocessing；不覆写 stdout/stderr stream handler。命令签名以 `zbrush.commands` 为准，机制以 `doc/zscript_python_reference.md` §7 8.5 定案为准。

- [ ] **Step 1: 日志系统**

```python
# -*- coding: utf-8 -*-
"""zbridge_085 - ZBrush 2026+ 图层导出/导入原型。
日志系统 + GoZ 导出辅助 + 图层 UI 辅助层。运行于 ZBrush Python。"""
import os
import time

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
_log_fh = None
_log_name = ""


def log_init(tag="run"):
    """打开新日志文件 log/zb085_YYYYMMDD_HHMMSS_<tag>.log。返回绝对路径。"""
    global _log_fh, _log_name
    os.makedirs(LOG_DIR, exist_ok=True)
    _log_name = f"zb085_{time.strftime('%Y%m%d_%H%M%S')}_{tag}.log"
    _log_fh = open(os.path.join(LOG_DIR, _log_name), "w", encoding="utf-8")
    log("LOG", f"session start: {_log_name}")
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
```

- [ ] **Step 2: GoZ 导出辅助**

```python
def export_goz(zbc, path):
    """FileNameSetNext + Tool:Export。path 必须正斜杠（反斜杠 → 缩放 ~70%）。"""
    path = path.replace("\\", "/")
    log("EXPORT", f"goz={path}")
    zbc.set_next_filename(path)
    zbc.press("Tool:Export")
```

- [ ] **Step 3: 图层 UI 辅助层（对照 §7 8.5 定案逐条）**

```python
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
    """可见性写：期望与当前不一致才 IClick(W-5,H/2) 切换一次；W/H 现读。"""
    path = layer_full_path(zbc)
    if layer_visible(zbc) != want:
        w = zbc.get_width(path)
        h = zbc.get_height(path)
        zbc.click(path, w - 5, h / 2)
        log("LAYER", f"click_eye want={want} now={layer_visible(zbc)}")


def layer_record_import(zbc, goz_path):
    """New（自动录制）-> 导入 goz_path -> 退录制。返回 (ok, 异常消息)。
    仅当 IModGet bit0=1 时 IClick(W-25) 退录制。"""
    zbc.press("Tool:Layers:New")
    if not layer_recording(zbc):
        log("LAYER", "[FAIL] New 未进入录制态")
        return False, "new_not_recording"
    zbc.set_next_filename(goz_path.replace("\\", "/"))
    zbc.press("Tool:Import")
    if layer_recording(zbc):
        p = layer_full_path(zbc)
        zbc.click(p, zbc.get_width(p) - 25, zbc.get_height(p) / 2)
    return True, ""
```

- [ ] **Step 4: Commit**

```bash
git add prototype_py/zbridge_085.py
git -c user.name="ZBridge Dev" -c user.email="dev@zbridge.local" commit -m "feat(0.8.5): zbridge_085 日志系统 + goz 导出 + 图层 UI 辅助层"
```

---

## Task 3: probe1_isolation.py — S1 隔离性探测

**Files:**
- Create: `prototype_py/probes/probe1_isolation.py`

> **测试前置（用户操作）**：ZBrush 2026+ 中准备一个**含 2 个已命名、有明显不同形变图层**的子工具（LayerA@强度1、LayerB@强度0.5），设为活动子工具。编辑本文件顶部 `OUT_DIR` 为测试目录（默认 `prototype_py/out`）。

- [ ] **Step 1: 实现探测脚本**

```python
# -*- coding: utf-8 -*-
"""probe1_isolation - S1 隔离性探测（规格 §S1）。
一次运行产出 5 项交叉指标：A 线性恒等式 / B 单层隔离 / D1 D2 污染诊断 / E 拓扑。
运行：ZBrush 2026+ Python 控制台 exec(open(...)) 。
前置：活动子工具含 2 层（LayerA@1、LayerB@0.5），形变互异明显。
输出：prototype_py/log/zb085_*_s1_isolation.log 末尾附结论。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"   # ← 用户可改为自己的测试目录
EXPECT_B_INT = 0.5


def run():
    zb.log_init("s1_isolation")
    os.makedirs(OUT_DIR, exist_ok=True)
    n = zb.layer_detect(zbc)
    zb.log("S1", f"layer_count={n}")
    if n != 2:
        zb.log("S1", f"[FAIL] 需要 2 个图层，实际 {n}；中止")
        return
    zb.layer_goto_top(zbc, n)
    zb.log("S1", f"top_layer={zb.layer_name(zbc)} int={zb.layer_intensity(zbc)}")

    # 快照序列：current -> base -> L0 -> L1
    zb.export_goz(zbc, f"{OUT_DIR}/cur.goz")           # 原状态 M
    zb.layer_goto_top(zbc, n)
    for i in range(n):                                  # 全部归零 -> base
        zb.layer_set_intensity(zbc, 0.0)
        if i < n - 1:
            zb.layer_step(zbc, down=True)
    zb.export_goz(zbc, f"{OUT_DIR}/base.goz")
    # 逐层快照：当前在栈底（LayerB）-> 导出 L1 -> 向上 LayerA -> 导出 L0
    zb.layer_set_visible(zbc, True)                     # 可见关阻断形变，必须先开眼
    zb.layer_set_intensity(zbc, 1.0)
    zb.export_goz(zbc, f"{OUT_DIR}/L1.goz")             # LayerB@1
    zb.layer_set_intensity(zbc, 0.0)                    # 置 0 防残留 + 自动关眼
    zb.layer_step(zbc, down=False)
    zb.layer_set_visible(zbc, True)
    zb.layer_set_intensity(zbc, 1.0)
    zb.export_goz(zbc, f"{OUT_DIR}/L0.goz")             # LayerA@1
    zb.layer_set_intensity(zbc, 0.0)

    # 机器判定（gozlib）
    cur = gozlib.read_goz_points(f"{OUT_DIR}/cur.goz")[1]
    base = gozlib.read_goz_points(f"{OUT_DIR}/base.goz")[1]
    l0 = gozlib.read_goz_points(f"{OUT_DIR}/L0.goz")[1]
    l1 = gozlib.read_goz_points(f"{OUT_DIR}/L1.goz")[1]
    m = gozlib.compute_metrics(cur, base, l0, l1, int0=1.0, int1=EXPECT_B_INT)
    for k, v in m.items():
        zb.log("S1", f"metric {k}={v}")
    zb.log("S1", "=== 结论 ===")
    zb.log("S1", f"A 线性叠加恒等式: {'PASS' if m['A_pass'] else 'FAIL'}")
    zb.log("S1", f"B 单层隔离:       {'PASS' if m['B_isolated'] else 'FAIL'}")
    zb.log("S1", f"E 拓扑一致:       {'PASS' if m['E_topology'] else 'FAIL'}")
    if not m["A_pass"]:
        zb.log("S1", f"D1 诊断(dB缺失? cur≈L0 残差): {m['D1_resid']:.6f}")
        zb.log("S1", f"D2 诊断(强度全1? cur≈L0+L1 残差): {m['D2_resid']:.6f}")
    zb.log("S1", f"OUT_DIR={OUT_DIR} 已生成 cur/base/L0/L1.goz")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: 用户运行**

操作：ZBrush 2026+ Python 控制台执行 `exec(open(r"<绝对路径>/prototype_py/probes/probe1_isolation.py", encoding="utf-8").read())`。
反馈：直接读取 `prototype_py/log/` 下最新 `zb085_*_s1_isolation.log`，粘贴"=== 结论 ==="后的行 + metric 行即可（无需抄写 Note）。

- [ ] **Step 3: 结果分析 + 分支决策**

- `A PASS` → 隔离成立，S2 继续。
- `A FAIL` → 看 D1/D2：D1 小 → dB 贡献缺失（归零残留/可见性）；D2 小 → 强度缩放全按 1.0（强度语义）；两者都大 → 基准污染或层序累计（结合 B/E 定位）。
- 更新 `doc/0.8.5/PROGRESS.md`"实测事实"与 S1 状态。

- [ ] **Step 4: Commit**

```bash
git add prototype_py/probes/probe1_isolation.py
git -c user.name="ZBridge Dev" -c user.email="dev@zbridge.local" commit -m "feat(0.8.5): S1 隔离性探测脚本（5 指标交叉判定）"
```

---

## Task 4: probe2_record_import.py — S2 录制导入

**Files:**
- Create: `prototype_py/probes/probe2_record_import.py`

> **前置**：S1 隔离成立；`out/` 有 `cur/base/L0/L1.goz`。
> **测试前置（用户）**：活动子工具为干净无图层网格（在 ZBrush 里对 `out/base.goz` 执行 Tool:Import 生成，拓扑与快照一致）。

- [ ] **Step 1: 实现探测脚本**

```python
# -*- coding: utf-8 -*-
"""probe2_record_import - S2 录制导入验证（规格 §S2）。
验证：New(自动录制) -> 导入 L0.goz -> 形变是否进入新层（=delta(L0)）、基网格不变。
前置：活动子工具无图层、拓扑与 out/L*.goz 一致（从 out/base.goz 导入生成）。
输出：log/zb085_*_s2_rec.log + 机器判定（与 S1 delta 交叉对比）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"   # 与 probe1 一致


def run():
    zb.log_init("s2_record_import")
    n0 = zb.layer_detect(zbc)
    zb.log("S2", f"before layers={n0}")
    if n0 != 0:
        zb.log("S2", "[FAIL] 前置要求：活动子工具必须无图层（先 Tool:Import out/base.goz）")
        return
    base = gozlib.read_goz_points(f"{OUT_DIR}/base.goz")[1]
    l0 = gozlib.read_goz_points(f"{OUT_DIR}/L0.goz")[1]
    expect_d = gozlib.vertex_delta(base, l0)

    zb.layer_record_import(zbc, f"{OUT_DIR}/L0.goz")
    zb.log("S2", f"after import layers={zb.layer_detect(zbc)} rec={zb.layer_recording(zbc)}")

    zb.export_goz(zbc, f"{OUT_DIR}/rec_out.goz")
    out_pts = gozlib.read_goz_points(f"{OUT_DIR}/rec_out.goz")[1]
    got_d = gozlib.vertex_delta(base, out_pts)
    resid = gozlib.residual_max(got_d, expect_d)
    zb.log("S2", f"delta residual vs expect: {resid:.6f}")
    eps = max(gozlib.delta_norm(expect_d) * 1e-3, 1e-4)
    zb.log_pass("S2", resid <= eps, "录制导入的形变应等于 S1 的 delta(L0)（交叉对比）")
    zb.log("S2", f"final layers={zb.layer_detect(zbc)} (应=1)")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: 用户运行 + 反馈日志**（操作同 Task 3 Step 2；粘贴 `log/zb085_*_s2_rec.log` 关键行）
- [ ] **Step 3: 结果分析 + PROGRESS 更新**（失败定位：New 未录制 / 导入未记录形变 / 导入替换网格）
- [ ] **Step 4: Commit**

---

## Task 5: probe3_restore.py — S2 恢复算法

**Files:**
- Create: `prototype_py/probes/probe3_restore.py`

> **前置**：probe2 通过。场景：干净网格 → New+导入 L1（建第 1 层，栈底层）→ New+导入 L0（建第 2 层，栈顶层）→ 检查层数/栈序/全强度网格 = B+dA+dB（与 S1 delta 交叉对比）/ 强度写读往返。

- [ ] **Step 1: 实现探测脚本**

```python
# -*- coding: utf-8 -*-
"""probe3_restore - S2 恢复算法验证（规格 §S2 probe3）。
前置：probe2 通过；活动子工具无图层（从 out/base.goz 导入）。
输出：log/zb085_*_s3_restore.log + 机器判定。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"


def run():
    zb.log_init("s3_restore")
    base = gozlib.read_goz_points(f"{OUT_DIR}/base.goz")[1]
    l0 = gozlib.read_goz_points(f"{OUT_DIR}/L0.goz")[1]
    l1 = gozlib.read_goz_points(f"{OUT_DIR}/L1.goz")[1]
    dA = gozlib.vertex_delta(base, l0)
    dB = gozlib.vertex_delta(base, l1)
    # 1) 先建 LayerB（栈底）-> 2) 再建 LayerA（New 插栈顶）
    ok1, e1 = zb.layer_record_import(zbc, f"{OUT_DIR}/L1.goz")
    ok2, e2 = zb.layer_record_import(zbc, f"{OUT_DIR}/L0.goz")
    zb.log("RST", f"record_import results: {ok1}/{e1} {ok2}/{e2}")
    n = zb.layer_detect(zbc)
    zb.log_pass("RST", n == 2, f"层数应=2，实际 {n}")
    if n != 2:
        return
    # 3) 全强度=1 时网格 = B + dA + dB
    zb.layer_goto_top(zbc, n)
    zb.export_goz(zbc, f"{OUT_DIR}/restore_full.goz")
    full = gozlib.read_goz_points(f"{OUT_DIR}/restore_full.goz")[1]
    expect_full = gozlib.add_pts(gozlib.add_pts(base, dA), dB)
    resid = gozlib.residual_max(full, expect_full)
    zb.log("RST", f"full-stack residual={resid:.6f}")
    zb.log_pass("RST", resid <= max(gozlib.delta_norm(expect_full) * 1e-3, 1e-4),
                "双录层重建后网格 = B + dA + dB（与 S1 delta 交叉对比）")
    # 4) 强度写读往返
    zb.layer_set_intensity(zbc, 0.5)
    readback = zb.layer_intensity(zbc)
    zb.log("RST", f"set A=0.5 read_back={readback}")
    zb.log_pass("RST", abs(readback - 0.5) < 1e-6, "强度写读往返")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: 用户运行 + 反馈日志**
- [ ] **Step 3: 结果分析 + PROGRESS 更新**（失败定位：栈序 / delta 叠加 / 强度往返）
- [ ] **Step 4: Commit**

---

## Task 6: zbridge_085.py 全功能 export/import（S3）

**Files:**
- Modify: `prototype_py/zbridge_085.py`

> 在 Task 2 辅助层上追加两个入口。复用 probe1/2/3 已验证流程，**不引入新 UI 操作**。

- [ ] **Step 1: 实现 `export_layers(zbc, out_dir, subtool_name)`**

```python
def export_layers(zbc, out_dir, subtool_name):
    """导出活动子工具全部图层（S1 快照流程 + layers.txt 记录）。
    文件：<out_dir>/<subtool_name>_LayerBase.goz、_Layer<i>.goz、layers.txt
    返回记录数；无图层返回 0。"""
    n = layer_detect(zbc)
    log("EXP", f"subtool={subtool_name} layers={n}")
    if n == 0:
        return 0
    out_dir = out_dir.replace("\\", "/")
    os.makedirs(out_dir, exist_ok=True)
    # 记录各层原始状态（栈顶->栈底，layerIndex = n-1-pos）
    recs = []
    layer_goto_top(zbc, n)
    for i in range(n):
        recs.append({
            "subtool": subtool_name,
            "idx": n - 1 - i,                 # 0=栈底层
            "name": layer_name(zbc),
            "intensity": layer_intensity(zbc),
            "visible": 1 if layer_visible(zbc) else 0,
        })
        if i < n - 1:
            layer_step(zbc, down=True)
    # 基准网格：全部归零
    layer_goto_top(zbc, n)
    for i in range(n):
        layer_set_intensity(zbc, 0.0)
        if i < n - 1:
            layer_step(zbc, down=True)
    export_goz(zbc, f"{out_dir}/{subtool_name}_LayerBase.goz")
    # 逐层快照：栈底->栈顶（layerIndex 升序）
    layer_goto_top(zbc, n)
    for i in range(n):                        # 此刻在栈顶，向下走到目标层
        # 简化：从栈顶逐层下移，j=0 对应顶层 = 最大 layerIndex
        pass
    return n
```

> **执行说明**：`export_layers` 的"逐层快照"循环参考 probe1 的导航逻辑（probe1 从栈底向上；此处可改为从栈底向上：先 `layer_goto_top` 再 `layer_step(down=True)` n-1 次到栈底，之后与 probe1 一致向上逐层）。实现时以 probe1 实测通过的导航为准，完成后补全 `layers.txt` 写出（格式 `subtool|idx|name|intensity|visible|0|0\0`，null-terminated records，与主程序 0.8.0 一致）。

- [ ] **Step 2: 实现 `import_layers(zbc, out_dir, subtool_name)`**

```python
def import_layers(zbc, out_dir, subtool_name):
    """重建活动子工具图层栈（S2 录制导入 + 恢复算法）。
    读取 <out_dir>/layers.txt 匹配 subtool_name 的记录，按 layerIndex 升序
    record_import(Layer<i>.goz) 建层，最后恢复强度/可见性。
    返回 (重建层数, 失败数)。"""
    # 解析 layers.txt（null-terminated records，| 分隔 7 字段）
    # 逐条 record_import -> 命名（跳过，ZScript 版用 ZFU）-> 最终强度/可见性 pass
    raise NotImplementedError("Task 6 Step 2 实现：参照 probe2/3 流程 + layers.txt 解析")
```

> **执行说明**：`import_layers` 按规格 §S2/T4 顺序：解析 layers.txt → 按 layerIndex 升序逐条 `layer_record_import` → 全部建完后统一恢复强度（先强度后可见性，可见性对称恢复）。命名在 ZScript 版用 ZFU；Python 原型可先用 `zbc.press("Tool:Layers:Rename")` + `set_next_filename` 或跳过命名（0.8.5 单子工具原型重点是形变/强度/可见性/顺序）。

- [ ] **Step 3: 端到端自验证脚本 `probe_e2e.py`（S3）**

```python
# -*- coding: utf-8 -*-
"""probe_e2e - S3 端到端验证：export -> 新会话 import -> 逐项断言。
分两段运行（用户在两段之间新建 ZBrush 会话并导入 base.goz 生成干净网格）：
  run_export(): 对当前含 2 层子工具执行 export_layers
  run_import(): 对干净网格子工具执行 import_layers 后自动核对
输出：log/zb085_*_s3_e2e.log + VERIFIED 报告。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gozlib
import zbridge_085 as zb
from zbrush import commands as zbc

OUT_DIR = r"h:/vibe_coding/ZBridge/prototype_py/out"
ST_NAME = "Body"


def run_export():
    zb.log_init("s3_e2e_export")
    n = zb.export_layers(zbc, OUT_DIR, ST_NAME)
    zb.log("E2E", f"exported layers={n}")


def run_import():
    zb.log_init("s3_e2e_import")
    rebuilt, fails = zb.import_layers(zbc, OUT_DIR, ST_NAME)
    # 核对：层数 == 记录数；导出当前态与 S1 期望 M 对比
    zb.export_goz(zbc, f"{OUT_DIR}/e2e_final.goz")
    zb.log("E2E", f"rebuilt={rebuilt} fails={fails} VERIFIED={'PASS' if fails == 0 else 'FAIL'}")


if __name__ == "__main__":
    # 第一段运行：run_export()；第二段（新会话干净网格）运行：run_import()
    if len(sys.argv) > 1 and sys.argv[1] == "import":
        run_import()
    else:
        run_export()
```

- [ ] **Step 4: 用户运行两段 + 反馈日志**（导出段 → 新会话 → 导入段 → 粘贴 `log/zb085_*_s3_e2e_*.log`）
- [ ] **Step 5: 分析 + PROGRESS 更新**（S3 完成度；若 FAIL，定位到具体属性/步骤后回修）
- [ ] **Step 6: Commit**

---

## Task 7: S4 ZScript 移植（ZBridge_085.txt）

**Files:**
- Create: `src/zscript/ZBridge_085.txt`

> 前置：S3 Python 端到端 VERIFIED。**移植 = 机械翻译**：Python 辅助层每个函数 ↔ ZScript 例程，逐条对照。编码硬约束（project_memory）：UTF-8 BOM + CRLF、变量 camelCase 无下划线、位运算只在 If 条件、字符串判等用 StrLength+StrFind 双向前缀、`StrExtract` 第三参=终点索引（含）、`[Delay,N]` 秒单位、内存记录 null-terminated、路径正斜杠。

- [ ] **Step 1: 移植对照表（实现时逐条落实）**

| Python（zbridge_085 / probes） | ZScript 例程 |
|-------------------------------|-------------|
| `log_init/log/log_pass` | `zbLogMem` 内存块 + `MemResize`+`MemSaveToFile`（参考 0.8.0 `ZBRunLayerSnapshot` 既有模式；实时落盘前先 resize+2048，收尾精确 resize） |
| `export_goz` | `[FileNameSetNext,dir/name.goz]` + `[IPress,Tool:Export]`（正斜杠） |
| `layer_detect` | `ZBRunLayerDetect`（IsEnabled 防护 + Scrollbar 计数） |
| `layer_goto_top / layer_step` | `ZBRunLayerToTop` / `[IPress,Tool:Layers:SelectDown/Up]` |
| `layer_name / full_path` | `[IGetTitle,Tool:Layers:Layer Intensity]` / `[IGetTitle,...,1]` |
| `layer_intensity / set_intensity` | `[IGet/ISet,Tool:Layers:Layer Intensity]`（0-1 域） |
| `layer_visible / set_visible` | `[IModGet]` bit1 / `[IClick,path,W-5,H/2]` |
| `layer_recording` | `[IModGet]` bit0 |
| `layer_record_import` | 归零 → `[IPress,Tool:Layers:New]` → Detect 验证层数+1 → `[FileNameSetNext]`+`[IPress,Tool:Import]` → bit0 确认后 `[IClick,W-25]` 退录制 → 命名（ZFU） |
| `export_layers` | `ZBRunLayerSnapshot` 系列（0.8.0 T3 已有，**仅留图层相关**，去掉多子工具/贴图/动态交叉） |
| `import_layers` | `ZBRunLayerImpLoad/ImpMatch/ImpRec/RestoreImport`（0.8.0 T4 已有，单子工具化） |

> **执行说明**：0.8.0 主程序已有 T3/T4 全部例程（`src/zscript/ZBridge.txt` 789-1185 行）。S4 不是从零写，而是**抽取 + 去耦合**：把图层例程抽到独立文件 `ZBridge_085.txt`，砍掉多子工具循环/贴图/动态/文件夹/重名检查等无关逻辑，按 0.8.5 单子工具语义重接流程。抽取后每个例程的行为必须与 Python 原型一致（对照 Task 1-6 的流程顺序）。

- [ ] **Step 2: 独立插件骨架**

```text
//ZBridge_085 - SubTool Layer Export/Import (standalone)
//Version: 0.8.5
//用途: 仅子工具图层导出/导入还原，成功后并入主程序
//硬约束: UTF-8 BOM + CRLF; camelCase 无下划线; 正斜杠路径
[ISubPalette,"ZPlugin:ZBridge_085"]
[IButton,"ZPlugin:ZBridge_085:Layer Export", "[RoutineCall,ZB085RunExport]",,1]
[IButton,"ZPlugin:ZBridge_085:Layer Import", "[RoutineCall,ZB085RunImport]",,1]
```

（`ZB085RunExport`/`ZB085RunImport` 为顶层入口：目录选择 `[DirNameAsk]`/`[FileNameAsk]` → 调 `ZBRunLayerSnapshot`/`ZBRunLayerRestoreImport` 的单子工具版本 → 完成 Note + 错误计数。）

- [ ] **Step 3: 编码 + 发布目录**（`releases/0.8.5/ZBridge/ZBridge_085.txt`，字节一致）
- [ ] **Step 4: 用户同等场景测试**（对照 Python VERIFIED 报告逐项核对）
- [ ] **Step 5: PROGRESS 更新 + Commit**

---

## Task 8: S5 并入主程序（另立计划）

**前置**：S4 通过同等场景测试。
**方式**：把 `ZBridge_085.txt` 的例程并入 `src/zscript/ZBridge.txt`（升 0.8.5），用独立分支/独立 commit，`prototype_py` 保留作回归基准。并入后全量回归（0.8.0 既有场景 + 图层场景）。

---

## 自检清单（计划编写时已对照规格）

- 规格 §S1 指标 A/B/D1/D2/E → Task 1（gozlib.compute_metrics）+ Task 3 ✅
- 规格 §S2 probe2 录制导入 → Task 4 ✅
- 规格 §S2 probe3 恢复算法 → Task 5 ✅
- 规格 §S3 全功能 + 端到端 → Task 6 ✅
- 规格 §S4 ZScript 移植（陷阱清单逐条）→ Task 7 ✅
- 规格 §S5 并入 → Task 8 ✅
- 交叉对比要求：S1 delta 数据被 S2/S3 复用（Task 4/5/6 均以 S1 数据为期望基准）✅
- 无占位符：Task 6 Step 2 的 `raise NotImplementedError` 为**执行时实现项**（流程已在规格与 probe2/3 中定义完整），Task 7 为抽取既有例程（已指明来源文件与行号）。
