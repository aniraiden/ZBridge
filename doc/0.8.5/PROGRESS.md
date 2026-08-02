# 0.8.5 进度记录（续档入口）

> 阅读顺序：**先看本文件** → 结论与下一步 → 需要细节再看 `2026-08-02-layer-plugin-design.md`（规格）。
> 规则：每完成一个阶段，把结论写进"结论记录"；每发现新事实/陷阱，追加到"实测事实"。

## 阶段状态

| 阶段 | 内容 | 状态 | 结论 |
|------|------|------|------|
| S0 | 备份与目录规划 | ✅ 完成 | git commit `90d5399`；.gitignore 就绪 |
| S1 | 隔离性 spike | ⬜ 未开始 | — |
| S2 | 录制导入 + 恢复算法 spike | ⬜ 未开始 | — |
| S3 | Python 全功能原型 | ⬜ 未开始 | — |
| S4 | ZScript 移植 | ⬜ 未开始 | — |
| S5 | 并入主程序 | ⬜ 未开始 | — |

## 结论记录

### S0（2026-08-02）
- 基线备份：`git init` + 全部文件 commit `90d5399`（含主程序 v0.8.0、releases、tests、doc、refrenece）。
- .gitignore：排除 `debug.log`、`__pycache__/`、`*.pyc`、`prototype_py/log/`。
- 目录：新建 `doc/0.8.5/`、`prototype_py/` 骨架；`tests/` 既有文件不动。

## 实测事实（新发现，随时追加）

（空）

## 下一步行动

1. 用户评审规格文档 `doc/0.8.5/2026-08-02-layer-plugin-design.md`。
2. 通过后：S1 隔离性 spike（写 `prototype_py/probes/probe1_isolation.py` + 日志系统 + goz 解析器）。
