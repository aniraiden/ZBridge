[中文版](#中文版) | [English](#english)

---

# 中文版

# ZBridge

ZBrush 跨版本工程迁移插件：让高版本 ZBrush 创建的 Tool 尽可能无损地迁移到低版本 ZBrush（如 2026 → 2024）。

完全基于官方 GoZ SDK，不解析 ZTL/ZPR。Mesh、UV、Polypaint、Texture、Material 全部交给 GoZ，插件只负责记录 GoZ 无法表达的 Tool 状态。

## 功能

- **Export**：遍历全部 SubTool，导出 GoZ + manifest
- **Import**：读取 manifest，循环导入 GoZ，恢复 Tool 状态
- 支持 Folder 结构重建、可见性恢复、细分级别还原、重复子工具名检查
- 动态细分预览属性恢复（8 项）、颜色纹理重绑定
- Sculpt Layer 快照（各层 GoZ + layers.txt 元数据）— ⚠️ 开发中（0.8.5：层恢复/层名恢复尚未实现）

## 工程格式

导出产物为目录（无打包，ZIP 可自行完成）：

```text
导出目录/
├── zbridge_manifest.txt   # 全部 SubTool 元数据
├── Body.goz               # 以子工具名命名
├── Hair.goz
└── ...
```

## 使用

1. 高版本 ZBrush 中点击 **Export**，选择导出目录
2. 低版本 ZBrush 中点击 **Import**，选择同一目录

## 目录结构

```text
├── src/
│   ├── zscript/           # ZBrush 插件主脚本（ZBridge.txt）
│   └── cpp/               # GoZ 二进制读写工具源码
├── doc/                   # 设计文档与开发日志
├── prototype_py/          # Python 原型与 GoZ 解析探针
├── tests/                 # ZScript 测试脚本
└── releases/              # 历史发布版本
```

## 版本

当前版本 0.8.0，详见 [doc/ZBridge.md](doc/ZBridge.md)（[英文版](doc/ZBridge_EN.md)）。

---

# English

# ZBridge

A ZBrush cross-version tool migration plugin: transfer Tools created in newer ZBrush versions to older ones with minimal loss (e.g. 2026 → 2024).

Built entirely on the official GoZ SDK; no ZTL/ZPR parsing. Mesh, UV, Polypaint, Texture and Material are all handled by GoZ — the plugin only records the Tool state that GoZ cannot express.

## Features

- **Export**: iterate all SubTools, export GoZ + manifest
- **Import**: read manifest, import GoZ in a loop, restore Tool state
- Folder structure reconstruction, visibility restore, subdivision level restore, duplicate subtool name check
- Dynamic subdivision preview attribute restore (8 attrs), color texture rebind
- Sculpt Layer snapshots (per-layer GoZ + layers.txt metadata) — ⚠️ in development (0.8.5: layer restore/layer rename not implemented yet)

## Project Format

The export output is a directory (no packaging; ZIP can be done manually):

```text
export_dir/
├── zbridge_manifest.txt   # metadata of all SubTools
├── Body.goz               # named after the subtool
├── Hair.goz
└── ...
```

## Usage

1. Click **Export** in the newer ZBrush, choose the export directory
2. Click **Import** in the older ZBrush, choose the same directory

## Directory Layout

```text
├── src/
│   ├── zscript/           # main plugin script (ZBridge.txt)
│   └── cpp/               # GoZ binary read/write utilities
├── doc/                   # design docs and development log
├── prototype_py/          # Python prototypes and GoZ parsing probes
├── tests/                 # ZScript test scripts
└── releases/              # past releases
```

## Version

Current version 0.8.0. See [doc/ZBridge.md](doc/ZBridge.md) / [English](doc/ZBridge_EN.md) for details.
