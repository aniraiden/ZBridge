# ZBridge 架构设计文档

## 1. 概述

ZBridge 是一个 ZBrush 插件，基于官方 GoZ SDK 传输网格数据，并附带自研 Recovery Engine 恢复 Tool 状态，实现跨版本 Tool 迁移。

**核心原则：GoZ 负责几何数据，ZBridge 负责工程状态。**

## 2. 系统架构（当前实现，v0.5.0）

```
┌──────────────────────────────────────────────────┐
│                    ZBrush                          │
│  ┌────────────────────────────────────────────┐   │
│  │          ZBridge 插件 (ZBridge.txt)          │   │
│  │  ┌──────────────────────────────────────┐  │   │
│  │  │      UI 模块 (IButton)               │  │   │
│  │  │  Export | Import | About             │  │   │
│  │  └────────┬──────────┬──────────┬───────┘  │   │
│  │           │          │          │           │   │
│  │  ┌────────┴──┐ ┌─────┴────┐ ┌───┴────────┐  │   │
│  │  │  Export   │ │  Import  │ │  Recovery  │  │   │
│  │  │  Routine  │ │ Routine  │ │   Engine   │  │   │
│  │  └────────┬──┘ └─────┬────┘ └────────┬───┘  │   │
│  │           │          │               │       │   │
│  │  ┌────────┴──────────┴───────────────┴────┐  │   │
│  │  │   Manifest (zbridge_manifest.txt)      │  │   │
│  │  │   管道分隔 | null 终止                  │  │   │
│  │  └───────────────────┬───────────────────┘  │   │
│  └──────────────────────┼──────────────────────┘   │
│                  GoZ SDK │ Tool:Export/Import        │
└─────────────────────────┼──────────────────────────┘
                          │
                 ┌────────┴─────────┐
                 │    导出目录        │
                 │  ├ Body.goz       │
                 │  ├ Hair.goz       │
                 │  ├ ...            │
                 │  └ zbridge_       │
                 │    manifest.txt   │
                 └──────────────────┘
```

## 3. 模块定义

### 3.1 UI 模块

- **位置：** `ZBridge.txt` 内部（单文件架构）
- **面板：** `ZPlugin:ZBridge`
- **按钮：**
  - `Export For Older Version` — 触发导出流程
  - `Import From Newer Version` — 触发导入流程
  - `About ZBridge` — 显示版本与平台信息

### 3.2 Export 例程（`ZBRunExport`）

- **入口：** `[RoutineCall,ZBRunExport]`
- **流程：**
  1. 通过 `[IGetTitle,Tool:Item Info]` 获取当前 Tool 名称
  2. 通过 `[SubToolGetCount]` 获取 SubTool 数量
  3. 通过 `[FileNameAsk]` 让用户选择保存位置（`.goz` 文件，用作目录参考）
  4. 通过 `[FileNameExtract,path,1]` 提取目录
  5. 通过 `[MemCreate,zbManMem,32768]` 创建 manifest 内存块
  6. **重名检查（v0.5.0）：** 遍历 SubTool 收集名称（`[IGetTitle]` 去尾 2 字符，与 manifest 一致）两两比对，发现重名即中止导出并弹窗列出（详见 `ZBRunDupCheck`）
  7. 遍历每个 SubTool：
     - `[SubToolSelect,idx]` 切换选中
     - `[IGetTitle,Tool:Item Info]` 获取名称（去尾字符）
     - 通过 `[SubToolGetStatus]` 判定是否文件夹、读取可见性位
     - 通过 `[SubToolGetFolderName]` 获取所属文件夹名
     - 获取 Colorize 状态 `[IGet,Tool:Polypaint:Colorize]`
     - 获取当前/最高细分 `[IGet,Tool:Geometry:SDiv]` + `[IGetMax,Tool:Geometry:SDiv]`
     - 切到最高 SDiv 后导出（高精度网格）
     - 写入 manifest 记录（null 终止）
     - `[FileNameSetNext,gozPath]` + `[IPress,Tool:Export]` 导出 `<子工具名>.goz`
     - 导出后恢复原 SDiv
  7. `[MemResize]` 裁剪 manifest 内存块到精确大小
  8. `[MemSaveToFile]` 保存 manifest 到目录
  9. 恢复原活动 SubTool

### 3.3 Import 例程（`ZBRunImport`）

- **入口：** `[RoutineCall,ZBRunImport]`
- **流程：**
  1. 让用户选择导出目录中的任一 `.goz` 文件（用于定位目录）
  2. `[FileNameExtract,path,1]` 提取目录
  3. 读取 `zbridge_manifest.txt` 并解析记录
  4. **Phase 1 纯导入：** 首个 GoZ 通过 `Tool:Import` 导入为主 Tool；后续 GoZ 通过 `Duplicate + Import` 追加为 SubTool
  5. **Phase 2 属性恢复：** 按 manifest 恢复名称、Colorize、细分级别、可见性
  6. **Phase 3 文件夹重建：** New Folder + MoveUp 重建文件夹结构
  7. 报告结果

### 3.4 Recovery Engine（集成于 Import 例程）

按 manifest 逐项恢复：

1. **SubTool 名称** — `.dat` 文件导入法
   - 创建以原名命名的空 `.dat` 文件
   - `[FileNameSetNext]` + `[IPress,Tool:Import]` 使其按文件名命名
   - `[ISet,Tool:Item Info,zbMainToolID]` 切回主 Tool，重新选中正确索引
2. **Colorize 状态** — `[ISet,Tool:Polypaint:Colorize,flag]`（先 `[IExists]` 判空）
3. **细分级别** — `[IPress,Tool:Geometry:Reconstruct Subdiv]` 循环 `maxSdiv-1` 次重建级别，再 `[ISet,Tool:Geometry:SDiv,currentSdiv]`
4. **可见性** — `[SubToolSetStatus,idx,status]`，位运算必须用 If 判断 + 加减法（见 §5.5）
5. **文件夹结构** — 见 §5.4

### 3.5 Manifest 格式（`zbridge_manifest.txt`）

- **格式：** 管道分隔、null 终止记录，所有 SubTool 存于单一文件
- **记录格式：** `colorize|maxSdiv|curSdiv|subtoolEye|folderEye|isFolder|isOpened|folderName|name\0`
- **示例：**
```
1|4|3|1|0|0|0||Body\01|4|3|1|1|1|1|CharacterFolder|Character\0...
```
- **写入：** `[MemWriteString]` 附加 null 终止字符串
- **读取：** `[MemCreateFromFile]` 加载，`[MemReadString]` 自动在 null 处停止

## 4. 数据流

### Export

```
ZBrush Tool
    │
    ├── 遍历每个 SubTool:
    │   ├── 名称 / Colorize / 当前与最高 SDiv / 文件夹信息 ──→ manifest 记录
    │   └── GoZ 导出 ───────────────→ <子工具名>.goz（最高 SDiv）
    │
    └── zbridge_manifest.txt（全部记录单文件）
```

### Import

```
导出目录
    │
    ├── <子工具名>.goz ──→ Phase 1 导入（首个 Import，其余 Duplicate+Import）
    │
    └── zbridge_manifest.txt
        └── Phase 2：按记录恢复名称 / Colorize / 细分 / 可见性
        └── Phase 3：重建文件夹结构
```

## 5. 关键技术方案

### 5.1 SubTool 追加策略

**问题：** `Tool:SubTool:Append` 弹出手动选择窗口，无法自动化。
**方案：** `Duplicate + Import`：
1. 切到主 Tool → 选择最后一个 SubTool → Duplicate → 选择新 SubTool → `Tool:Import` 导入 GoZ（替换网格，保留 SubTool 结构）。

### 5.2 名称恢复（.dat 导入法）

**问题：** ZScript 无直接"重命名 SubTool"命令。
**方案：**
1. 创建名为 `原名.dat` 的空文件
2. `[FileNameSetNext]` + `[IPress,Tool:Import]`，ZBrush 自动以文件名命名 SubTool
3. `[ISet,Tool:Item Info,zbMainToolID]` 切回主 Tool，重新选中正确索引

### 5.3 细分级别恢复

**问题：** GoZ 格式不保存细分级别。
**方案：** 记录 maxSdiv/curSdiv；导入后 `Reconstruct Subdiv` 循环 `maxSdiv-1` 次，再 `[ISet,Tool:Geometry:SDiv,curSdiv]`。

### 5.4 文件夹结构重建

**问题：** 扁平导入后文件夹结构丢失。
**方案：** New Folder + MoveUp：
1. 从下往上处理文件夹，`SubToolSelect` → `[IPress,Tool:SubTool:New Folder]` 包裹文件夹头
2. 用 ZFileUtils `RenameSetNext` 重命名文件夹
3. `SubToolSetStatus` 展开文件夹（0x800）
4. 逐个 `[IPress,Tool:SubTool:MoveUp]` 将内容子工具移入
5. 恢复可见性与展开/关闭状态

文件夹身份判定：`(status & 0x400) OR (status & 0x800)`（0x400=关闭，0x800=展开）。**不能用 0x002 单独判定**——关闭文件夹不设置 0x002 位。

### 5.5 位运算安全模式

**关键发现（0.4.0）：** ZScript 的 `|` 和 `&` 位运算符在 `[VarSet]` 赋值上下文中不可靠（可能返回 0），但在 `[If]` 条件判断中可用。

```
正确：If,(status & 1) == 0, VarSet,status,status + 1   （设置 bit0）
正确：If,(status & 2) == 2, VarSet,status,status - 2   （清除 bit1）
错误：VarSet,status,status | 1                          （不可靠）
错误：VarSet,status,status & 2147483645                 （不可靠）
```

### 5.6 单文件 Manifest

**问题：** 每条记录一个 `.man` 文件会导致 IO 性能差。
**方案：** 全部记录存于一个 `zbridge_manifest.txt`，用内存块写入/读取。

## 6. 错误处理策略

1. **预检：** 校验 Tool 已加载、SubTool 存在
2. **文件校验：** 文件操作前 `[FileExists]`
3. **用户确认：** `[Note]` 带 Proceed/Cancel 按钮
4. **错误计数：** 跟踪导入错误，结束时报告
5. **优雅退出：** Tool 缺失或取消操作时 `[Exit]`

## 7. 文件结构

```
ZBridge/
├── src/
│   ├── cpp/                          # GoZ SDK C++ 参考（插件不使用）
│   │   ├── GoZ_Binary.h
│   │   ├── GoZ_Config.h
│   │   ├── GoZ_Mesh.cpp / GoZ_Mesh.h
│   │   └── GoZ_Utils.cpp / GoZ_Utils.h
│   └── zscript/
│       └── ZBridge.txt               # 单文件插件源码（v0.5.0）
├── tests/                            # ZScript 测试与调试脚本
├── doc/
│   ├── ZBridge.md                    # 项目规格
│   ├── architecture.md               # 本文档（当前实现架构）
│   ├── design_0.2.0.md               # 0.2.0 设计文档（历史）
│   ├── design_next.md                # 新功能设计（基于 0.4.0）
│   ├── zscript_python_reference.md   # ZScript/Python 命令参考
│   └── development_log.md            # 开发日志（含 0.4.0 回退记录）
├── tools/
│   └── pack_release.ps1              # 发布打包脚本
└── releases/
    ├── 0.1.0/                        # MVP
    ├── 0.2.0/                        # +文件夹与可见性记录
    ├── 0.3.0/                        # +文件夹重建
    ├── 0.4.0/                        # +可见性修复（0.5.0 的基线）
    └── 0.5.0/                        # +子工具重名检查（当前版本）
```

**注意：** `.zbridge` 单文件打包功能（旧 0.5.0/0.6.0 版本号）已在 0.4.0 回退中取消，不保留 release 存档。**版本号重计**：新的 0.5.0 从 0.4.0 基线开发，含义为"子工具重名检查"，与历史 0.5.0/0.6.0（.zbridge 打包）不同。详见 `development_log.md` 的"0.4.0 回退"与"0.5.0"章节。

## 8. ZScript 语法要求

### 8.1 文件编码

- **BOM：** 必须为 UTF-8 with BOM（EF BB BF）
- **行尾：** 必须为 CRLF
- ZBrush 解析器在 LF-only 或无 BOM 时静默失败

### 8.2 变量命名

- **不支持下划线**：使用 camelCase（`zbCount`，而非 `zb_count`），下划线会被解析器拆分
- `[VarDef]` 仅在顶层使用；例程内用 `[VarSet]`

### 8.3 文件扩展名

- 源码使用 `.txt`（`.zsc` 是编译格式）
- 通过 ZScript 面板 > Load 按钮加载

### 8.4 已验证命令

- `[SubToolGetCount]`、`[SubToolSelect,idx]`、`[SubToolGetActiveIndex]`
- `[SubToolGetStatus,idx]`、`[SubToolSetStatus,idx,flags]`、`[SubToolGetFolderName,idx]`
- `[IGetTitle,Tool:Item Info]`、`[IGet,Tool:Item Info]`、`[ISet,Tool:Item Info,id]`
- `[IGet,Tool:Polypaint:Colorize]`、`[ISet,Tool:Polypaint:Colorize,flag]`
- `[IGet,Tool:Geometry:SDiv]`、`[IGetMax,Tool:Geometry:SDiv]`、`[ISet,Tool:Geometry:SDiv,val]`
- `[IsEnabled,Tool:Geometry:Reconstruct Subdiv]`、`[IPress,Tool:Geometry:Reconstruct Subdiv]`
- `[IPress,Tool:SubTool:New Folder]`、`[IPress,Tool:SubTool:MoveUp]`、`[IPress,Tool:SubTool:MoveDown]`
- `[MemCreate]`、`[MemDelete]`、`[MemResize]`、`[MemWriteString]`、`[MemReadString]`、`[MemSaveToFile]`、`[MemCreateFromFile]`
- `[StrMerge]`、`[StrExtract]`、`[StrLength]`、`[StrFind]`、`[StrFromAsc]`
- `[FileNameAsk]`、`[FileNameSetNext]`、`[FileNameExtract]`、`[FileExists]`、`[FileDelete]`
- `[Val]`、`[VarDef]`、`[VarSet]`、`[VarInc]`

**不支持（已验证报错）：**

- `[ISubToolGetCount]` → 用 `[SubToolGetCount]`
- `[IGet,"Tool:Name"]` → 用 `[IGetTitle,Tool:Item Info]`
- `[IPress,"SubTool:Previous/Next"]` → 用 `[SubToolSelect,idx]`
- `[MemReadFromFile]` → 用 `[MemCreateFromFile]`
- `[StrFind]` 带字符串：仅支持 `[StrFind,"substr",var]` 或 `[StrFind,"substr",var,startpos]`
