# 0.8.5 进度记录（续档入口）

> 阅读顺序：**先看本文件** → 结论与下一步 → 需要细节再看 `2026-08-02-layer-plugin-design.md`（规格）。
> 规则：每完成一个阶段，把结论写进"结论记录"；每发现新事实/陷阱，追加到"实测事实"。

## 阶段状态

| 阶段 | 内容 | 状态 | 结论 |
|------|------|------|------|
| S0 | 备份与目录规划 | ✅ 完成 | git commit `90d5399`；.gitignore 就绪 |
| S1 | 隔离性 spike | ✅ 完成 | **隔离成立**：A 残差 5.96e-08（浮点级）、B/E PASS；7938 顶点 |
| S2 | 录制导入 + 恢复算法 spike | ⬜ 未开始 | — |
| S3 | Python 全功能原型 | ⬜ 未开始 | — |
| S4 | ZScript 移植 | ⬜ 未开始 | — |
| S5 | 并入主程序 | ⬜ 未开始 | — |

## 结论记录

### S0（2026-08-02）
- 基线备份：`git init` + 全部文件 commit `90d5399`（含主程序 v0.8.0、releases、tests、doc、refrenece）。
- .gitignore：排除 `debug.log`、`__pycache__/`、`*.pyc`、`prototype_py/log/`。
- 目录：新建 `doc/0.8.5/`、`prototype_py/` 骨架；`tests/` 既有文件不动。

### S1（2026-08-02，probe1 真实 ZBrush 运行 + 机器判定）
- **结论：图层隔离性成立，强度滑杆线性（0-1 域）实锤**。
- 真实数据：cur/base/L0/L1.goz 各 7938 顶点；`A_pass=True`（残差 5.96e-08）；`B_isolated=True`（dA=0.973、dB=0.887）；`D1=D2=0.4436`（恰为 0.5×dB，与 LayerB@0.5 精确吻合）。
- 数值模型定案：`current = base + Σ intensity_i × delta_i`（delta_i = Layer_i@1 - base）。
- 眼图标点击**有效**（L0/L1 均抓到真实形变）；但点击后立即 IModGet 读取滞后（`now=False` 假象），已从日志中移除该读回、不设状态门。
- 过程 bug：gozlib 用 `GOZ_TAG_POINT_LIST=10000`，真实 ZBrush 写 `10001`（C 枚举 BASE_ID+1）→ 首跑假阳性 `counts=[0,0,0,0]`；修复后回归测试 + 真实文件可选回归测试（`out/cur.goz` 存在时）双保险。

## 实测事实（新发现，随时追加）

- **ZBrush 2026.1 无 Python 交互控制台**：脚本通过 ZScript 面板 → *Python Scripting* 子面板 → **Load** 按钮加载即执行（Reload 重跑上次脚本）；命令行方式为 `ZBrush.exe -script "script.py"`（ZPR 文件放最后参数）。控制台输出需在 *Script Window Mode* 切 *Python Output* 模式（官方 quickstart 2026-08-02 查证；日志文件才是主反馈通道）。官方 hello_world 示例确认标准 `if __name__ == "__main__"` 保护约定。


## 下一步行动

1. **S2 录制导入 + 恢复算法**：写并运行 `probe2_record_import.py`（New 自动录制 + 导入形变进层）→ `probe3_restore.py`（双录层重建 + 强度/可见性恢复），均以 S1 的 base/L0/L1 delta 为交叉基准。
2. S3 全功能原型（export_layers/import_layers + 端到端）。
3. S4 ZScript 移植、S5 并入主程序。
