# -*- coding: utf-8 -*-
"""test_zbridge_mock - 本地 mock 端到端（无需 ZBrush）。
用 MockZBC 模拟 ZBrush 图层栈/网格模型（语义对齐实测：New 插栈底、IClick 按名首匹配、
滑杆=当前层、强度0 自动关眼、MoveUp/Down 交换、Import 后层 delta=导入网格-基准），
跑 export_layers -> 清空 -> import_layers，验证记录/快照文件/重建层数/强度/可见性/最终网格。
运行：python prototype_py/test_zbridge_mock.py（开发机独立 Python）。"""
import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gozlib
import zbridge_085 as zb

TAG_POINT_LIST = 10001


def build_goz(path, pts):
    """构造最小 goz（与真实 ZBrush 同：POINT_LIST tag=10001）。"""
    out = b"GoZb" + b" " * 28

    def block(tag, icount, payload):
        return struct.pack("<IIIf", tag, 16 + len(payload), icount, 0.0) + payload

    out += block(1, 1, b"Mock\x00" + b"\x00" * 4)
    pts_b = struct.pack("<%df" % (len(pts) * 3), *[c for p in pts for c in p])
    out += block(TAG_POINT_LIST, len(pts), pts_b)
    out += block(0, 0, b"")
    with open(path, "wb") as f:
        f.write(out)


class MockZBC:
    """最小 ZBrush 命令模拟。layers = [栈顶 -> 栈底]。"""

    def __init__(self, base_pts):
        self.base_pts = list(base_pts)
        self.layers = []
        self.cur = 0
        self.next_file = ""
        self.sdiv = 1.0
        self.sdiv_max = 4.0
        self._rec_start = list(base_pts)  # 录制起点：New 按下瞬间的当前网格

    # ---- 模型 ----
    def _find_by_name(self, name):
        for i, lay in enumerate(self.layers):
            if lay["name"] == name:
                return i
        return None

    def _name_from_path(self, path):
        return path.split(":")[-1]

    def _current(self):
        return self.layers[self.cur]

    def current_mesh(self):
        pts = list(self.base_pts)
        for lay in self.layers:
            if lay["delta"] is not None and lay["vis"] and lay["int"] != 0.0:
                pts = gozlib.add_pts(pts, gozlib.add_scaled(lay["delta"], lay["int"]))
        return pts

    # ---- 命令面 ----
    def exists(self, path):
        return True

    def get_width(self, path):
        return 100.0

    def get_height(self, path):
        return 20.0

    def get_max(self, path):
        if "SDiv" in path:
            return self.sdiv_max
        return 5.0

    def is_enabled(self, path):
        if "Layer Intensity" in path:
            return len(self.layers) > 0
        if "Rename" in path:
            return len(self.layers) > 0
        if "SDiv" in path:
            return True
        return False

    def get_title(self, path, full_path=False):
        if path == "Tool:Item Info":
            return "Body1"
        name = self._current()["name"]
        return f"Tool:Layers:{name}" if full_path else name

    def get(self, path):
        if "Layer Intensity" in path:
            return self._current()["int"]
        if "SDiv" in path:
            return float(self.sdiv or 1)
        return 0.0

    def get_secondary(self, path):
        return float(len(self.layers) - 1) if "Scrollbar" in path else 0.0

    def get_mod(self, path):
        idx = self._find_by_name(self._name_from_path(path))
        if idx is None:
            return 0
        lay = self.layers[idx]
        return (1 if lay["rec"] else 0) | (2 if lay["vis"] else 0)

    def set(self, path, h_value=None, v_value=None):
        if "Layer Intensity" in path:
            v = float(h_value)
            lay = self._current()
            if lay["int"] == 0.0 and v > 0.0:
                lay["vis"] = True  # 2026.1 实测：强度从0设到>0 自动开眼
            lay["int"] = v
            if v == 0.0:
                lay["vis"] = False
        elif "SDiv" in path:
            self.sdiv = float(h_value)

    def set_next_filename(self, path):
        self.next_file = path

    def click(self, path, x, y):
        idx = self._find_by_name(self._name_from_path(path))
        if idx is None:
            return
        lay = self.layers[idx]
        if x >= 85.0:      # W-5 眼
            lay["vis"] = not lay["vis"]
        else:              # W-25 退录制
            lay["rec"] = False

    def press(self, path):
        if path == "Tool:Layers:New":
            self.layers.append({"name": "Untitled Layer", "int": 1.0, "vis": False, "rec": True, "delta": None})
            self.cur = len(self.layers) - 1
            self._rec_start = self.current_mesh()  # 录制起点 = New 瞬间当前网格（含可见层贡献）
        elif path == "Tool:Layers:MoveUp":
            if self.cur > 0:
                self.layers[self.cur], self.layers[self.cur - 1] = self.layers[self.cur - 1], self.layers[self.cur]
                self.cur -= 1
        elif path == "Tool:Layers:MoveDown":
            if self.cur < len(self.layers) - 1:
                self.layers[self.cur], self.layers[self.cur + 1] = self.layers[self.cur + 1], self.layers[self.cur]
                self.cur += 1
        elif path == "Tool:Layers:SelectUp":
            self.cur = max(0, self.cur - 1)
        elif path == "Tool:Layers:SelectDown":
            self.cur = min(len(self.layers) - 1, self.cur + 1)
        elif path == "Tool:Layers:Delete":
            if self.layers:
                del self.layers[self.cur]
                self.cur = min(self.cur, len(self.layers) - 1)
        elif path == "Tool:Layers:Rename":
            self._current()["name"] = self.next_file
        elif path == "Tool:Import":
            _, pts = gozlib.read_goz_points(self.next_file)
            if len(pts) != len(self._rec_start):
                # 2026-08-03 实测：录制导入时顶点数不匹配 -> Tool:Import 替换当前工具（丢图层、丢细分）
                self.layers = []
                self.cur = 0
                self.base_pts = list(pts)
                self.sdiv = 1.0
                return
            self._current()["delta"] = gozlib.vertex_delta(self._rec_start, pts)
        elif path == "Tool:Export":
            build_goz(self.next_file, self.current_mesh())


def near(a, b, eps=1e-6):
    # goz 存储为 float32（~1e-7 舍入），文件比对容差取 1e-6
    return gozlib.residual_max(a, b) <= eps


def rec_by_idx(recs, idx):
    for r in recs:
        if r["idx"] == idx:
            return r
    return None


def test_e2e_roundtrip():
    tmp = tempfile.mkdtemp(prefix="zbridge_mock_")
    try:
        OUT = tmp
        base = [(float(i), 0.0, 0.0) for i in range(8)]
        dA = [(0.5, 0.0, 0.0) if i < 4 else (0.0, 0.0, 0.0) for i in range(8)]
        dB = [(0.0, 0.0, 0.0) if i < 4 else (0.0, 0.3, 0.0) for i in range(8)]

        # 场景 1：用户子工具 Body，两层（栈顶=LayerB vis=False / 栈底=LayerA vis=True）
        m = MockZBC(base)
        m.layers = [
            {"name": "LayerB", "int": 1.0, "vis": False, "rec": False, "delta": dB},
            {"name": "LayerA", "int": 1.0, "vis": True,  "rec": False, "delta": dA},
        ]
        m.cur = 0
        n = zb.export_layers(m, OUT, "Body")
        assert n == 2, f"export 记录数 {n}"

        # 快照文件
        _, b0 = gozlib.read_goz_points(f"{OUT}/Body_LayerBase.goz")
        assert near(b0, base), "LayerBase 应=基准网格"
        _, l0 = gozlib.read_goz_points(f"{OUT}/Body_Layer0.goz")
        assert near(gozlib.vertex_delta(b0, l0), dA), "Layer0 应=A delta"
        _, l1 = gozlib.read_goz_points(f"{OUT}/Body_Layer1.goz")
        assert near(gozlib.vertex_delta(b0, l1), dB), "Layer1 应=B delta"

        # layers.txt 记录
        recs = zb.read_layers_txt(f"{OUT}/layers.txt")
        assert len(recs) == 2, f"记录数 {len(recs)}"
        r0 = rec_by_idx(recs, 0)
        r1 = rec_by_idx(recs, 1)
        assert r0["name"] == "LayerA" and r0["intensity"] == 1.0 and r0["visible"] is True, r0
        assert r1["name"] == "LayerB" and r1["intensity"] == 1.0 and r1["visible"] is False, r1

        # 导出后状态恢复（层序/强度/可见性复原）
        assert len(m.layers) == 2
        assert m.layers[0] == {"name": "LayerB", "int": 1.0, "vis": False, "rec": False, "delta": dB}
        assert m.layers[1] == {"name": "LayerA", "int": 1.0, "vis": True,  "rec": False, "delta": dA}

        # 场景 2：新会话干净网格（模拟用户导入 LayerBase.goz）
        m2 = MockZBC(gozlib.read_goz_points(f"{OUT}/Body_LayerBase.goz")[1])
        built, fails = zb.import_layers(m2, OUT, None)
        assert built == 2 and fails == 0, f"import built={built} fails={fails}"

        # 重建层序：栈顶=idx1(B)、栈底=idx0(A)；强度 1.0/1.0；可见性 False/True
        assert len(m2.layers) == 2, f"重建层数 {len(m2.layers)}"
        assert m2.layers[0]["int"] == 1.0 and m2.layers[0]["vis"] is False, m2.layers[0]
        assert m2.layers[1]["int"] == 1.0 and m2.layers[1]["vis"] is True, m2.layers[1]
        assert not m2.layers[0]["rec"] and not m2.layers[1]["rec"], "录制应已退出"

        # 最终网格 = base + dA（B 不可见不参与）
        final = m2.current_mesh()
        exp_off = zb.expected_mesh(OUT, "Body", recs, vis_blocks=True)
        exp_on = zb.expected_mesh(OUT, "Body", recs, vis_blocks=False)
        assert exp_off is not None and exp_on is not None
        assert near(final, exp_off), "最终网格应=base+dA（vis 阻断）"
        assert not near(final, exp_on), "不应等于全计"
        print("PASS test_e2e_roundtrip")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_e2e_roundtrip_3layers_rename_sdiv():
    """场景 3：3 层不同强度 + 层名恢复（重命名）+ SDiv>1 切换/恢复。
    栈顶=LayerC(1.0,隐藏) / LayerB(0.5,显示) / 栈底=LayerA(1.0,显示)。"""
    tmp = tempfile.mkdtemp(prefix="zbridge_mock3_")
    try:
        OUT = tmp
        base = [(float(i), 0.0, 0.0) for i in range(12)]
        dA = [(0.5, 0.0, 0.0) if i < 4 else (0.0, 0.0, 0.0) for i in range(12)]
        dB = [(0.0, 0.0, 0.0) if i < 4 else ((0.0, 0.3, 0.0) if i < 8 else (0.0, 0.0, 0.0)) for i in range(12)]
        dC = [(0.0, 0.0, 0.4) if i >= 8 else (0.0, 0.0, 0.0) for i in range(12)]

        m = MockZBC(base)
        m.sdiv = 1.0
        m.layers = [
            {"name": "LayerC", "int": 1.0, "vis": False, "rec": False, "delta": dC},
            {"name": "LayerB", "int": 0.5, "vis": True,  "rec": False, "delta": dB},
            {"name": "LayerA", "int": 1.0, "vis": True,  "rec": False, "delta": dA},
        ]
        m.cur = 0
        n = zb.export_layers(m, OUT, "Body")
        assert n == 3, f"export 记录数 {n}"

        # 快照文件：LayerBase=base，Layer<i>=base+di
        _, b0 = gozlib.read_goz_points(f"{OUT}/Body_LayerBase.goz")
        assert near(b0, base), "LayerBase 应=基准网格"
        for idx, d in ((0, dA), (1, dB), (2, dC)):
            _, li = gozlib.read_goz_points(f"{OUT}/Body_Layer{idx}.goz")
            assert near(gozlib.vertex_delta(b0, li), d), f"Layer{idx} delta 应纯净"

        # layers.txt 记录（强度 0.5 必须保留）
        recs = zb.read_layers_txt(f"{OUT}/layers.txt")
        assert len(recs) == 3, f"记录数 {len(recs)}"
        r0, r1, r2 = (rec_by_idx(recs, i) for i in (0, 1, 2))
        assert r0["name"] == "LayerA" and r0["intensity"] == 1.0 and r0["visible"] is True, r0
        assert r1["name"] == "LayerB" and r1["intensity"] == 0.5 and r1["visible"] is True, r1
        assert r2["name"] == "LayerC" and r2["intensity"] == 1.0 and r2["visible"] is False, r2

        # 导出后状态恢复（层序/强度/可见性/层名复原）+ SDiv 复原
        assert len(m.layers) == 3
        assert m.layers[0] == {"name": "LayerC", "int": 1.0, "vis": False, "rec": False, "delta": dC}, m.layers[0]
        assert m.layers[1] == {"name": "LayerB", "int": 0.5, "vis": True,  "rec": False, "delta": dB}, m.layers[1]
        assert m.layers[2] == {"name": "LayerA", "int": 1.0, "vis": True,  "rec": False, "delta": dA}, m.layers[2]
        assert m.sdiv == 1.0, f"导出后 SDiv 应复原 {m.sdiv}"

        # 新会话干净网格导入
        m2 = MockZBC(gozlib.read_goz_points(f"{OUT}/Body_LayerBase.goz")[1])
        m2.sdiv = 1.0
        built, fails = zb.import_layers(m2, OUT, None, rename=True)
        assert built == 3 and fails == 0, f"import built={built} fails={fails}"

        # 重建：层名恢复（mock 重命名成功）、层序、强度、可见性
        assert len(m2.layers) == 3, f"重建层数 {len(m2.layers)}"
        assert m2.layers[0]["name"] == "LayerC" and m2.layers[0]["int"] == 1.0 and m2.layers[0]["vis"] is False, m2.layers[0]
        assert m2.layers[1]["name"] == "LayerB" and m2.layers[1]["int"] == 0.5 and m2.layers[1]["vis"] is True, m2.layers[1]
        assert m2.layers[2]["name"] == "LayerA" and m2.layers[2]["int"] == 1.0 and m2.layers[2]["vis"] is True, m2.layers[2]
        assert not any(l["rec"] for l in m2.layers), "录制应已全部退出"

        # 最终网格 = base + dA + 0.5×dB（LayerC 隐藏）
        exp_off = zb.expected_mesh(OUT, "Body", recs, vis_blocks=True)
        exp_on = zb.expected_mesh(OUT, "Body", recs, vis_blocks=False)
        assert exp_off is not None and exp_on is not None
        assert near(m2.current_mesh(), exp_off), "最终网格应=base+dA+0.5dB（vis 阻断）"
        assert not near(m2.current_mesh(), exp_on), "不应等于全计"

        # SDiv 复原
        assert m2.sdiv == 1.0, f"导入后 SDiv 应复原 {m2.sdiv}"
        print("PASS test_e2e_roundtrip_3layers_rename_sdiv")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_import_vertex_mismatch_failfast():
    """场景 4：导入前当前网格顶点数与 goz 不一致（模拟用户重建细分/Divide 后）→ Tool:Import
    替换工具。import_layers 必须 fail-fast 中止（built=0），不得继续建层污染 delta。"""
    tmp = tempfile.mkdtemp(prefix="zbridge_mock4_")
    try:
        OUT = tmp
        base = [(float(i), 0.0, 0.0) for i in range(8)]
        dA = [(0.5, 0.0, 0.0) if i < 4 else (0.0, 0.0, 0.0) for i in range(8)]
        dB = [(0.0, 0.0, 0.0) if i < 4 else (0.0, 0.3, 0.0) for i in range(8)]
        m = MockZBC(base)
        m.layers = [
            {"name": "LayerB", "int": 1.0, "vis": False, "rec": False, "delta": dB},
            {"name": "LayerA", "int": 1.0, "vis": True,  "rec": False, "delta": dA},
        ]
        m.cur = 0
        zb.export_layers(m, OUT, "Body")

        # 模拟用户"重建细分"：导入 LayerBase 后把网格换成顶点数不同的网格（Divide 使顶点翻倍）
        m2 = MockZBC(gozlib.read_goz_points(f"{OUT}/Body_LayerBase.goz")[1])
        m2.base_pts = [(float(i), 0.0, 0.0) for i in range(20)]
        m2._rec_start = list(m2.base_pts)

        built, fails = zb.import_layers(m2, OUT, None)
        assert fails == 1, f"应 fail-fast 报 1 个失败，实际 fails={fails}"
        assert built == 0, f"fail-fast 后不应继续建层，实际 built={built}"
        assert len(m2.layers) == 0, f"工具替换后应无图层，实际 {len(m2.layers)}"
        print("PASS test_import_vertex_mismatch_failfast")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_e2e_roundtrip()
    test_e2e_roundtrip_3layers_rename_sdiv()
    test_import_vertex_mismatch_failfast()
    print("ALL PASS")
