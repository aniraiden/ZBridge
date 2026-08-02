# ZBridge 0.2.0 设计文档：文件夹结构 + 可见性恢复

## 一、目标

在 0.1.0 MVP 基础上增加两个能力，分三个阶段逐步实现与测试：

1. **文件夹结构恢复**：记录并重建 SubTool 文件夹层级
2. **可见性恢复**：记录并恢复各 SubTool 的眼睛可见状态

> 注：0.2.0 曾规划的 `.zbridge` 打包功能已在 0.4.0 回退中取消，本文档不再包含该部分，详见 `development_log.md`。

## 二、Manifest 格式

### 2.1 zbridge_manifest.txt（ZScript 实用格式）

管道分隔 + null 终止符，沿用已验证的 `MemWriteString`/`MemReadString`。扩展记录格式：

```
旧: colorize|maxSdiv|curSdiv|name\0
新: colorize|maxSdiv|curSdiv|subtoolEye|folderEye|isFolder|isOpened|folderName|name\0
```

字段说明：

| 字段 | 含义 |
|------|------|
| colorize | 1=有顶点色，0=无 |
| maxSdiv | 最高细分级别 |
| curSdiv | 当前细分级别 |
| subtoolEye | 子工具眼睛位（0x001），1=睁眼，0=闭眼。对文件夹头也是 bit0 |
| folderEye | 文件夹眼睛位（0x002），1=睁眼，0=闭眼。仅对文件夹头有意义；普通子工具恒为 0 |
| isFolder | 1=文件夹条目，0=网格子工具。通过 `(status & 0x400) OR (status & 0x800)` 判定 |
| isOpened | 1=展开（0x800 设置），0=关闭（0x400 设置）。仅对文件夹头有意义；普通子工具恒为 0 |
| folderName | 所属文件夹名（文件夹条目自身为空，文件夹不可嵌套） |
| name | 子工具名 / 文件夹名 |

**关键修正**（来自 Test0 Debug 实测）：
- 关闭文件夹的 `0x002` 位**不设置**，不能仅用 `0x002` 判定文件夹身份
- 关闭文件夹的 status 示例：`1041 = 0x1 + 0x10 + 0x400`（无 0x002）
- 展开文件夹的 status 示例：`2067 = 0x1 + 0x2 + 0x10 + 0x800`
- 文件夹身份正确判定：`(status & 0x400) OR (status & 0x800)`

**已知限制**（留待阶段三 Import 处理）：
- 当 folderName 为空时（`||` 相邻），`StrExtract` 返回 `|` 而非空字符串
- 文件夹条目的 folderName 本就为空，Import 阶段一/二跳过文件夹条目，不影响功能
- 阶段三 Import 使用 folderName 重建文件夹时需处理此边界情况（如用占位符或长度判断）

示例：

```
1|4|3|1|0|0|0||Body\0                         // Body 无文件夹，可见
1|4|3|1|1|1|1|CharacterFolder|Character\0     // Character 是展开且可见文件夹
0|2|2|1|0|1|0|PropFolder|Prop\0               // Prop 是关闭且不可见文件夹
0|2|2|1|0|0|CharacterFolder|Hair\0            // Hair 在 CharacterFolder 内，可见
```

## 三、Export 模块改动

遍历全部 SubTool 索引（含文件夹条目），通过 `[SubToolGetStatus,idx]` 判定类型：

| 条目类型 | 判定 | manifest 记录 | GoZ 导出 |
|---|---|---|---|
| 文件夹 | `(status & 0x400) OR (status & 0x800)` | isFolder=1, subtoolEye=bit0, folderEye=bit1, isOpened=(0x800?1:0), folderName=`[SubToolGetFolderName,idx]`, name=子工具名 | **导出**（文件夹头本身是网格模型） |
| 网格子工具 | 非文件夹 | isFolder=0, subtoolEye=bit0, folderEye=0, isOpened=0, folderName=`[SubToolGetFolderName,idx]` | 导出为 `<子工具名>.goz` |

**关键**：文件夹头既是文件夹标识又是网格模型，**所有条目都导出 GoZ 文件**。

**注意**：不能用 `0x002` 单独判定文件夹身份——关闭文件夹的 `0x002` 位不设置。文件夹身份必须通过 `0x400`（关闭）或 `0x800`（展开）位判定。

GoZ 文件以子工具名命名（`<子工具名>.goz`），与 manifest 同级。Manifest 记录全量子工具索引顺序（含文件夹），用于导入时重建结构。

ZFileUtils DLL 依赖：**不用于 Export**（读取文件夹名/状态全部用原生 ZScript API）。

## 四、Import 模块改动（三阶段）

### 4.1 阶段一：扁平导入

按 manifest 顺序，对 `isFolder=0` 的条目用现有 `Duplicate + Import` 策略导入为扁平子工具列表。文件夹条目跳过。得到无文件夹的扁平列表，顺序与导出时一致。

### 4.2 阶段二：可见性恢复（先于文件夹重建）

对每个 manifest 记录（按顺序）：

1. **名称恢复**：现有 `.dat` 导入法（文件夹条目跳过）
2. **可见性恢复**：
   - 网格子工具：`[SubToolSetStatus, idx, 0x001]` 开 / `[SubToolSetStatus, idx, 0x000]` 关
   - 文件夹条目此阶段不存在，留待阶段三结束后再统一设置
3. **Colorize / 细分恢复**：现有逻辑不变

此阶段验证可见性往返正确性，无文件夹结构干扰。

### 4.3 阶段三：文件夹结构重建

遍历 manifest 记录（保持原索引顺序），利用两个已验证行为：

- `New Folder` 自动包裹当前选中子工具
- 展开文件夹后，对紧随其后的子工具调用 `MoveUp` 可将其移入文件夹

算法：

```
对每个 folder 条目（按 manifest 顺序）:
  1. 找到该文件夹的第一个网格子工具（folderName==该文件夹名）
  2. SubToolSelect 该子工具
  3. ZFileUtils.RenameSetNext(文件夹名) + IPress("Tool:SubTool:New Folder")
     → 创建文件夹并命名，包裹该子工具
  4. 展开文件夹（SubToolSetStatus 设 OpenedFolder 0x800 位）
  5. 对该文件夹的每个后续子工具（按原索引顺序）:
     a. SubToolSelect 该子工具
     b. IPress("Tool:SubTool:MoveUp")  → 移入文件夹
```

依赖 `ZFileUtils64.dll` 的 `RenameSetNext`（项目 `refrenece/` 已自带），纯 ZScript 无法在 `New Folder` 时程序化命名。

**索引追踪**：文件夹创建与 MoveUp 会改变子工具索引。阶段三执行前，先按子工具名建立"manifest索引→当前扁平索引"映射；阶段三中通过名称（`SubToolGetFolderName` + 名称匹配）定位子工具，规避索引漂移。

阶段三结束后，对文件夹条目设置可见性（subtoolEye + folderEye 两个独立位）：

- 恢复原 subtoolEye：`[SubToolSetStatus, idx, status | 0x001]` 开 / `[SubToolSetStatus, idx, status & ~0x001]` 关
- 恢复原 folderEye：`[SubToolSetStatus, idx, status | 0x002]` 开 / `[SubToolSetStatus, idx, status & ~0x002]` 关
- 恢复原展开/关闭状态：`status | 0x800` 展开 / `status | 0x400` 关闭（注意互斥，需先清除对方位）
- 普通子工具：仅恢复 subtoolEye

**关键**：文件夹头和内在子工具的可见性独立——`subtoolEye` 控制子工具自身眼睛，`folderEye` 控制文件夹眼睛。Import 阶段二先恢复扁平子工具的 subtoolEye，阶段三文件夹重建后再恢复文件夹头的 folderEye + isOpened。

## 五、部署模型变化

0.1.0 是单文件。0.2.0 新增 DLL 依赖：

```
ZBridge/
├── ZBridge.txt              # 主插件
└── ZBridgeData/
    ├── ZFileUtils64.dll     # 文件夹命名支持（Windows）
    └── folder.txt           # 数据目录标记
```

Mac 对应 `ZFileUtils.lib`。DLL 加载与版本校验沿用 `refrenece/ZFileUtils_2021_01A/ZFileUtils_TestZScript_2021.txt` 的 `CheckSystem` 例程模式。

## 六、分阶段实现与测试计划

### 阶段一：Export 侧文件夹检测 + manifest 扩展

**实现**：
- Export 例程增加 SubToolGetStatus 文件夹检测（用 `0x400 | 0x800` 判定，非 `0x002`）
- manifest 记录扩展为 9 字段：subtoolEye / folderEye / isFolder / isOpened / folderName
- GoZ 文件以子工具名命名（`<子工具名>.goz`）

**单元测试**（ZScript 测试文件 `tests/test4_folder_status.txt`）：
- Debug 原始 status 值：验证关闭/展开文件夹的实际状态位
- 文件夹检测：0x400 | 0x800 位运算
- 可见性读写：SubToolGetStatus/SetStatus bit0 往返
- manifest 9 字段格式读写：MemWriteString/MemReadString 多字段

**集成测试**：
- 导出含文件夹的工程，检查 manifest 字段完整性

### 阶段二：Import 侧可见性恢复（扁平）

**实现**：
- Import 后增加可见性恢复逻辑（网格子工具 SetStatus 0x001/0x000）

**单元测试**：
- 可见性读写在导入后的正确性

**集成测试**：
- 扁平子工具（无文件夹）可见性往返

### 阶段三：Import 侧文件夹结构重建

**实现**：
- New Folder + MoveUp 重建策略
- ZFileUtils DLL 加载与 RenameSetNext 调用
- 索引漂移规避（名称定位）

**集成测试**：
- 完整文件夹结构 + 可见性往返
- 多文件夹、嵌套子工具顺序、可见性组合

## 七、风险与降级方案

### 7.1 MoveUp 入文件夹行为

基于用户洞察与命令验证（`Tool:SubTool:MoveUp` 在 ZBrush 宏中实际使用），但需在真实 ZBrush 2024/2026 中功能验证。若 MoveUp 行为不符预期（例如只是上移而非入文件夹），降级方案：

- New Folder 仅包裹首个子工具
- 其余子工具作为文件夹外同级
- 文件夹结构部分恢复，不阻断其余功能

### 7.2 DLL 依赖

0.2.0 从单文件变为文件+DLL。若需保持单文件部署，降级方案：

- 文件夹默认命名（ZBrush 自动命名 Folder 1/Folder 2...）
- 文件夹名无法自动恢复，需用户手动改名
- 其余功能（可见性、网格子工具恢复）不受影响

## 八、已验证的 ZScript 命令（0.2.0 新增）

在 [architecture.md 第八章](architecture.md#8-zscript-syntax-requirements) 已验证命令基础上，0.2.0 新增：

| 命令 | 用途 | 验证来源 |
|------|------|----------|
| `[SubToolGetStatus, idx]` | 读取状态位域（含文件夹/可见性） | ZBrushCentral marcus_civis |
| `[SubToolSetStatus, idx, flags]` | 设置状态位域 | ZBrushCentral marcus_civis |
| `[SubToolGetFolderIndex, idx]` | 获取所属文件夹索引（-1=无） | Maxon Python API 确认 |
| `[SubToolGetFolderName, idx]` | 获取所属文件夹名（空=无） | Maxon Python API 确认 |
| `[IPress,Tool:SubTool:New Folder]` | 创建文件夹（包裹当前选中） | Maxon 用户指南 |
| `[IPress,Tool:SubTool:MoveUp]` | 子工具上移（可入展开文件夹） | ZBrushCentral 宏代码 |
| `[IPress,Tool:SubTool:MoveDown]` | 子工具下移 | ZBrushCentral 宏代码 |

状态位域：

| 位 | 值 | 含义 |
|----|----|------|
| 0x001 | Subtool Eye | 网格子工具可见性 |
| 0x002 | Folder Eye | 文件夹可见性 |
| 0x400 | ClosedFolder | 文件夹关闭状态 |
| 0x800 | OpenedFolder | 文件夹展开状态 |

**关键警告（0.4.0 发现）**：ZScript 的 `|` 和 `&` 位运算符在 `[VarSet]` 赋值上下文中**不可靠**（可能返回 0 或无效值），即使在 `[If]` 条件判断中可用。设置位状态时必须使用 If 判断 + 加减算术：
```
正确：If,(status & 1) == 0, VarSet,status,status + 1      （设置 bit0）
正确：If,(status & 2) == 2, VarSet,status,status - 2      （清除 bit1）
错误：VarSet,status,status | 1                              （不可靠！）
错误：VarSet,status,status & 2147483645                     （不可靠！）
```

## 九、ZFileUtils DLL 调用（0.2.0 新增）

用于文件夹命名。调用模式沿用 `refrenece/ZFileUtils_2021_01A/ZFileUtilsInc.txt`：

```
// 加载 DLL
[VarSet,dllPath,"路径/ZFileUtils64.dll"]
[VarSet,zfuOK,[FileExecute,dllPath,"Version"]]

// 程序化命名文件夹
[FileExecute,dllPath,"RenameSetNext",folderName]
[IPress,"Tool:SubTool:New Folder"]
```

DLL 加载失败时的降级：跳过程序化命名，使用 ZBrush 默认文件夹名。
