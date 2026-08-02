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
