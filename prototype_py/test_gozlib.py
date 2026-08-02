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
