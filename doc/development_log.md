# ZBridge 开发日志

## 版本总览

| 版本 | 内容 | 状态 |
|------|------|------|
| 0.1.0 | MVP：GoZ 导出/导入、SubTool、名称/顺序 | ✅ 归档 |
| 0.2.0 | 文件夹与可见性 | ✅ 归档 |
| 0.3.0 | 文件夹结构重建（New Folder + MoveUp + ZFileUtils） | ✅ 归档 |
| 0.4.0 | 名称/Colorize/细分级别恢复、单文件 manifest | ✅ 归档（开发基线） |
| 0.5.0 | 子工具重名检查（功能一，后续功能前置） | ✅ 归档 |
| 0.6.0 | 动态细分预览 8 属性还原（功能二，manifest ext 字段） | ✅ 归档 |
| 0.7.0 | 颜色贴图还原 / 贴图重新贴回（功能四，manifest ext 字段） | ✅ 当前版本（0.7.10 验证通过） |
| 0.8.0 | 雕刻图层还原（功能三，layers.txt + GoZ 快照，方案 A 录制导入） | 🚧 T4 首测全流程跑通；导出快照内容/导入 k=0 替换待修（小规模测试中） |

> 版本策略：新功能每项递增版本号（0.7.0+），release 存档于 `releases/<版本>/ZBridge/`（ZBridge.txt + ZBridgeData/）。
> 当前 manifest 记录格式：`colorize|maxSdiv|curSdiv|subtoolEye|folderEye|isFolder|isOpened|folderName|name|ext\0`。

---

## 版本：0.1.0 (MVP)
## 日期：2026-07-16
## 状态：已完成（归档）

---

## 一、已完成功能模块

### 1. UI 模块
- ZPlugin 面板下创建 `ZBridge` 子面板
- 三个按钮：Export For Older Version / Import From Newer Version / About ZBridge
- About 按钮显示 ZBridge 版本、ZBrush 版本、平台信息

### 2. Export 模块
- 自动遍历当前 Tool 的所有 SubTool
- 每个.SubTool 导出为独立的 `SubTool_N.goz` 文件
- 导出时自动切换到最高细分级别（高精度网格）
- 导出后恢复原细分级别
- 生成 `zbridge_manifest.txt` 记录所有 SubTool 元数据

### 3. Import 模块
- 扫描目录中的 `SubTool_N.goz` 文件
- 第一个 GoZ 文件通过 `Tool:Import` 创建主 Tool
- 后续 GoZ 文件通过 `Duplicate + Import` 添加为 SubTool
- 保持 SubTool 顺序与导出时一致

### 4. Recovery Engine（恢复引擎）
- **名称恢复**：通过 `.dat` 文件导入方法重命名 SubTool
- **顶点色恢复**：根据 manifest 记录开启/关闭 Colorize
- **细分级别恢复**：通过 Reconstruct Subdiv 重建级别，恢复到原始当前级别

### 5. Manifest 数据文件
- 单一文件 `zbridge_manifest.txt`
- 管道分隔格式：`colorize|maxSdiv|currentSdiv|name`
- 每条记录以 null 终止符分隔
- 使用内存块写入/读取，支持数百个 SubTool

---

## 二、关键技术实现

### 2.1 SubTool 追加策略
**问题**：`Tool:SubTool:Append` 会弹出选择窗口，无法自动化
**解决方案**：Duplicate + Import 方法
```
1. 切换到主 Tool
2. 选择最后一个 SubTool
3. Duplicate 复制
4. 选择新的（复制出来的）SubTool
5. Tool:Import 导入 GoZ（替换 mesh，保留 SubTool 结构）
```

### 2.2 SubTool 名称恢复
**问题**：ZScript 没有直接重命名 SubTool 的命令
**解决方案**：.dat 文件导入法
```
1. 创建空文件，文件名为原始 SubTool 名称 + .dat
2. FileNameSetNext + Tool:Import
3. ZBrush 自动以文件名命名 SubTool（去掉扩展名）
4. 切回主 Tool (ISet,Tool:Item Info,zbMainToolID)
5. 重新选择正确索引的 SubTool
```

### 2.3 细分级别完整恢复
**问题**：GoZ 格式不保存细分数据
**解决方案**：
- 导出时：记录 maxSdiv 和 currentSdiv，切到最高级别导出
- 导入后：Reconstruct Subdiv (maxSdiv-1) 次，再 ISet 到 currentSdiv

### 2.4 单文件 Manifest
**问题**：多文件方案影响 IO 性能
**解决方案**：
- 写入：`MemWriteString` 追加带 null 终止符的字符串到内存块
- 裁剪：`MemResize` 精确裁剪
- 保存：`MemSaveToFile` 一次性写入
- 读取：`MemCreateFromFile` 一次性加载，`MemReadString` 逐条读取

---

## 三、已解决的主要问题

### 3.1 "ZScript skipped due to error" 解析错误

| 问题 | 根因 | 修复 |
|------|------|------|
| `.zsc` 扩展名 | `.zsc` 是编译格式，源码必须用 `.txt` | 改为 `.txt` |
| 变量名含下划线 `zb_count` | ZScript 不支持下划线，解析器将其视为分隔符 | 全部改为驼峰命名 `zbCount` |
| 文件编码 | LF 行尾 + 无 BOM 导致解析失败 | UTF-8 BOM + CRLF |
| `<zscriptinsert, "path">` | 逗号后有空格 | 移除空格 |
| `[ISubToolGetCount]` | 不存在的命令 | 改用 `[SubToolGetCount]` |
| `[IGet,"Tool:Name"]` | 无效路径 | 改用 `[IGetTitle,Tool:Item Info]` |
| `[MemReadFromFile]` | 不存在的命令 | 改用 `[MemCreateFromFile]` |
| `[StrFind]` 用法 | 之前误以为不支持 | 实际支持，格式为 `[StrFind,"substr",var,startPos]` |
| `[VarDef]` 在 RoutineDef 内 | 只能在顶层使用 | 例程内改用 `[VarSet]` |
| RoutineDef 内空行 | 空行导致解析中断 | 移除所有空行 |

### 3.2 Import 功能问题

| 问题 | 根因 | 修复 |
|------|------|------|
| 只导入一个物体 | 所有 GoZ 都用 Tool:Import 导入 | 第一个用 Import，后续用 Duplicate+Import |
| Popup 选择报错 | 路径中 `\` 导致 StrMerge 拼接错误 | 放弃 Popup 方案，改用 Duplicate 方法 |
|材质错误 | Import 覆盖了材质 | Duplicate 方法保留了原有结构 |
| SubTool 名称丢失 | GoZ 不保存名称信息 | manifest 记录名称 + .dat 导入恢复 |
| 只恢复第一个 SubTool | .dat 导入后 Tool 切换丢失 | 添加 `ISet,Tool:Item Info,zbMainToolID` 切回 |
| 顶点色状态错误 | 字符串比较 `"1"` 不可靠 | 改用 `[Val,zbPpFlag] == 1` 数值比较 |
| 顶点色被 .dat 导入覆盖 | 操作顺序问题 | 调整为：名称恢复 → Colorize → 细分 |
| 细分多一级 | 循环次数错误 | 改为 maxSdiv - 1 次 |
| 细分未恢复到原级别 | 只重建了级别，未设置当前级别 | 添加 `ISet,Tool:Geometry:SDiv,currentSdiv` |

### 3.3 Export 功能问题

| 问题 | 根因 | 修复 |
|------|------|------|
| 弹出 Open 对话框 | FileNameAsk 默认文件名为空 | 设置默认文件名 `SubTool_0.goz` |
| 文件未生成 | 路径拼接缺少分隔符 | 直接使用 FileNameExtract 返回的目录 |

### 3.4 Manifest 格式演进

| 阶段 | 格式 | 问题 |
|------|------|------|
| V1 | JSON | 需要 StrFind/StrExtract 解析，复杂易错 |
| V2 | 每条记录一个 .man 文件 | 文件数过多，IO 性能差 |
| V3 | 单文件，null 终止符分隔 | 性能好，MemReadString 自动按 null 分隔 |

---

## 四、技术亮点

1. **零编译**：纯 ZScript 文本文件，无需编译环境
2. **单文件部署**：整个插件只有一个 `ZBridge.txt` 文件
3. **GoZ 原生**：完全基于 ZBrush 官方 GoZ SDK，不解析任何私有格式
4. **Recovery Engine**：通过 manifest + .dat 导入 + Reconstruct Subdiv 实现 Tool 状态完整恢复
5. **性能优化**：单文件 manifest，内存块操作，支持数百 SubTool
6. **跨版本兼容**：GoZ 格式在所有 ZBrush 版本间通用

---

## 五、验证结果

### 5.1 Export 验证
- 所有 SubTool 正确导出为独立 .goz 文件
- manifest 包含完整的 colorize/maxSdiv/currentSdiv/name 信息
- 导出后 Tool 状态恢复原样（SDiv、活动 SubTool）

### 5.2 Import 验证
- 所有 SubTool 正确导入为同一个 Tool 的不同 SubTool
- SubTool 顺序与导出时一致
- 多边形组保留
- 顶点色正确恢复（有→开，无→关）
- 细分级别正确恢复（级别数和当前级别）
- SubTool 名称正确恢复

### 5.3 已知限制
- GoZ 格式不保存细分数据，通过 Reconstruct Subdiv 重建（非原始数据）
- 导出的高精度 mesh 需要有足够的面数才能重建细分
- Folder 结构暂未支持
- 可见性状态暂未支持

---

## 六、下一步开发计划（更新于 2026-07-17）

| 优先级 | 功能 | 状态 |
|--------|------|------|
| 高 | `.zbridge` 打包 | ❌ 已回退（见 0.4.0 回退记录） |
| 高 | Folder 结构恢复 | ✅ 已完成（0.3.0） |
| 中 | 可见性恢复 | ✅ 已完成（0.2.0，0.4.0 修复） |
| 中 | 活动SubTool恢复 | 待实现 |
| 中 | 错误处理增强 | 待实现 |
| 低 | 进度条显示 | 待实现 |
| 低 | 多语言支持 | 待实现 |

---

## 七、文件清单

```
h:\vibe_coding\ZBridge\
├── src\zscript\ZBridge.txt              # 源文件 (8.9KB)
├── releases\0.1.0\ZBridge\ZBridge.txt   # 发布文件 (8.9KB)
├── tests\
│   ├── test0_minimal.txt                # 最小化测试
│   ├── test1_vars.txt                   # 变量测试
│   ├── test2_fix.txt                    # 循环+文件测试
│   ├── test3_include.txt                # include 测试
│   └── test3_inc_data.txt               # include 数据
├── doc\
│   ├── ZBridge.md                       # 项目规格文档
│   ├── architecture.md                  # 架构设计文档
│   └── development_log.md               # 本文档
└── reference\                           # ZScript 参考文件
```

---

## 版本：0.2.0 — 文件夹与可见性（Export/Import 基础）
## 日期：2026-07-16
## 状态：已完成

---

## 一、0.2.0 新增功能

### 1. Manifest 扩展（4→9 字段）
```
colorize|maxSdiv|curSdiv|subtoolEye|folderEye|isFolder|isOpened|folderName|name
```
- `subtoolEye`：子工具自身眼睛（bit0）
- `folderEye`：文件夹眼睛（bit1，控制文件夹+内容可见性）
- `isFolder`：是否为文件夹（通过 0x400/0x800 位检测，非 0x002）
- `isOpened`：文件夹展开/关闭状态
- `folderName`：文件夹名称（`[SubToolGetFolderName]` 获取）

### 2. 文件夹检测（关键发现）
- **0x002 位不可靠**：关闭的文件夹不设置 0x002 位
- **正确检测**：`(status & 0x400) == 0x400 OR (status & 0x800) == 0x800`
- 展开文件夹 status=2067（0x001+0x002+0x010+0x800），关闭文件夹 status=1041（0x001+0x010+0x400）
- 文件夹头本身也是网格模型，需一并导出 GoZ

### 3. Export 侧改动
- GoZ 文件命名从 `SubTool_N.goz` 改为 `{subtoolName}.goz`
- 所有条目（含文件夹头）均导出 GoZ
- manifest 9 字段记录完整状态信息

### 4. Import 侧改动（两阶段分离）
**Phase 1**：GoZ 文件导入（纯导入，不碰属性）
- 首个 GoZ 作为主 Tool 导入
- 后续通过 Duplicate + Import 追加
- GoZ 文件名即子工具名，无需 .dat 重命名

**Phase 2**：属性恢复（`SubToolSelect` 开头）
- Colorize 恢复（带 `[IExists]` 保护）
- SubDiv 恢复（Reconstruct Subdiv + SDiv 设置）
- Visibility 恢复：文件夹用 folderEye，普通子工具用 subtoolEye

### 5. GoZ Import 模式选择
| 方案 | 问题 |
|------|------|
| `Tool:SubTool:Append` | **不支持 GoZ 格式**，仅导入首个子工具 |
| `Duplicate + Import` | 已验证可用（0.1.0 同款） |
| 合并循环（Import+属性恢复） | 属性操作干扰 Import 状态，拓扑警告+位置错乱 |
| **两阶段分离**（最终方案） | Phase 1 纯导入 → Phase 2 纯恢复，稳定可靠 |

---

## 二、已解决的主要问题（0.2.0）

| 问题 | 根因 | 修复 |
|------|------|------|
| 关闭文件夹 isFolder=0 | 用 0x002 检测，关闭文件夹不设此位 | 改用 0x400/0x800 嵌套 If 检测 |
| 文件夹头未导出 GoZ | `If,zbIsFolder == 0` 跳过了文件夹 | 去掉条件，所有条目均导出 |
| folderName 字段为空 | Export 端对文件夹设了空字符串 | 改用 `[SubToolGetFolderName]` 获取 |
| Import 只导入首个 | Append 不支持 GoZ | 改回 Duplicate+Import |
| 拓扑警告+位置错乱 | 合并循环中属性操作干扰 Import | 拆为两阶段分离循环 |
| 编辑模式退出 | `ISet,Tool:Item Info` 用于非改名场景 | 仅 .dat 导入后用，GoZ Import 后不用 |
| Colorize 报错 | 新导入网格无 Polypaint 界面项 | 添加 `[IExists]` 保护 |
| 超长 StrMerge 解析失败 | ZScript 参数数量/长度限制 | 分步拼接（Test 3 + Export manifest line） |
| If 语句逗号位置 | 行尾内联 `,` 导致后续解析异常 | 逗号独占一行 |

---

## 三、验证结果（0.2.0）

### 单元测试（test4_folder_status.txt）
- Test 1 "Detect Folders"：4 个子工具正确区分，Prop 的 isFolder=1 ✓
- Test 2 "Visibility RW"：位运算往返（17→16→17）✓
- Test 3 "Manifest 9-Field"：9 字段写入/读取/解析完整 ✓
- Debug "Raw Status"：原始值 17/17/2067/1041 确认位定义 ✓

### 集成测试
- Export：4 个 GoZ 文件正确生成，manifest 9 字段完整 ✓
- Import：4 个子工具正确导入，名称/Body/Head/Character/Prop ✓
- Visibility：Body/Head/Character 可见，Prop 隐藏 ✓

### 已知限制（0.2.0）
- 文件夹结构未恢复（所有子工具扁平导入）
- flatten 导入后文件夹头变为普通子工具
- folderEye/folderName/isOpened 数据已记录，待 0.3.0 使用

---

## 版本：0.3.0 — 文件夹结构重建（Import Phase 3）
## 日期：2026-07-16
## 状态：已完成（后续 0.4.0 修复可见性 Bug）

---

## 一、0.3.0 新增功能

### 1. Import 侧文件夹结构重建（Phase 3）

在 Phase 1（GoZ 导入）和 Phase 2（属性恢复）之后，新增 Phase 3 将扁平子工具重建为文件夹结构。

**算法**：
1. 扫描 manifest 统计文件夹条目数
2. 从下往上处理每个文件夹（避免索引漂移）
3. 对每个文件夹：
   - `SubToolSelect` → `IPress,Tool:SubTool:New Folder` 包裹文件夹头
   - 用 ZFileUtils 重命名文件夹
   - 展开文件夹（SetStatus bit11=2048）
   - 逐个 MoveUp 将内容子工具移入
   - 恢复 visibility 和 open/close 状态

**索引计算**：`当前索引 = manifest索引 + (folderTotal - cursor - 1)`

**MoveUp 机制**：展开文件夹后，紧邻下方的子工具 MoveUp 进入文件夹，目标索引始终为 `zbCurSubIdx+2`。

### 2. ZFileUtils DLL 集成

内联 2 个关键例程：`ZFU_RenameSetNext`、`ZFU_RenameCurrentSubTool`。
DLL 路径：`ZBridgeData\ZFileUtils64.dll`（Win）/ `ZBridgeData/ZFileUtils.lib`（Mac）。
失败时降级：使用 ZBrush 默认文件夹名。

### 3. 部署结构

```
ZBridge/
├── ZBridge.txt
└── ZBridgeData/
    ├── ZFileUtils64.dll
    └── ZFileUtils.lib
```

---

## 二、新增/修改文件

| 文件 | 变更 |
|------|------|
| `src/zscript/ZBridge.txt` | v0.3.0；+`dllPath`/`zbFolderTotal`；+ZFileUtils 内联例程；Import 增加 DLL 加载 + Phase 3（~140行） |
| `releases/0.3.0/ZBridge/ZBridge.txt` | 同上 |
| `releases/0.3.0/ZBridge/ZBridgeData/` | 新增 DLL 文件 |

---

## 三、测试结果

| 项目 | 结果 |
|------|------|
| 回归 | 无文件夹场景 Phase 1+2 正常 ✓ |
| 单文件夹 | 1个文件夹 + 内容 → 正确重建 ✓ |
| 多文件夹 | 多个文件夹 → 正确重建 ✓ |
| bit10 展开/关闭 | open/close 状态正确保留 ✓ |
| bit0/bit1 可见性 | **失败**：导入后 b0=0, b1=HID（0.4.0 修复） |

## 四、发现的 Bug（0.4.0 修复）

### 4.1 文件夹可见性丢失
- **表现**：导出前 FOLDER b0=1 b1=VIS → 导入后 FOLDER b0=0 b1=HID
- **根因**：ZScript 的 `|` 和 `&` 位运算符在 `VarSet` 上下文中不可靠（可能返回 0 或无效值），导致 `SubToolSetStatus` 写入异常状态值
- **排查过程**：创建 Dump 测试脚本（step1）验证 bit 状态 → 发现原来两阶段（展开前+恢复）都未能正确设置位 → 尝试多种方法，定位到 VarSet 位运算失效
- **修复**：
  1. 移除所有 `VarSet,var,var | N` 和 `VarSet,var,var & N` 位运算
  2. 改用 If 判断 + 加减法：`If,(status & N) == 0, VarSet,status,status + N` / `If,(status & N) == N, VarSet,status,status - N`
  3. 合并两阶段为单阶段（New Folder → MoveUp → 一次性设所有位）
  4. Phase 2 可见性恢复也一并修复

### 4.2 ZScript 兼容性发现
- `&` 在 `[If,...]` 条件中可用，但在 `[VarSet,...]` 赋值中不可靠
- `|` 在任何 VarSet 上下文中均不可靠
- `\n` 换行符在 Note 中有效，但在部分 ZScript 解析器中可能被处理为字面量
- IPress/IWait 等 UI 交互命令在非 ZPlugin 加载的测试脚本中可能不可用

---
## 版本：0.4.0 — 文件夹可见性修复
## 日期：2026-07-16
## 状态：已完成

---

## 一、修复内容

### 1.1 文件夹可见性（bit0/bit1）丢失修复

**问题**：导入后文件夹的 bit0（容器可见）和 bit1（folEye/内容可见性）全部变为 0。

**根因**：ZScript 的 `|` 和 `&` 位运算符在 `[VarSet]` 赋值上下文中不可靠——`VarSet,var,var | 1` 可能产生 0 或无效值，导致 `SubToolSetStatus` 写入异常状态。

**修复**：
1. 用 If 判断 + 加减算术替代所有 VarSet 位运算：
   - `VarSet,status,status | 1` → `If,(status & 1)==0, VarSet,status,status+1`
   - `VarSet,status,status & ~2` → `If,(status & 2)==2, VarSet,status,status-2`
2. 合并展开+恢复两阶段为单阶段：New Folder → MoveUp → 一次性设置 bit0/bit1/bit10
3. Phase 2 可见性恢复（394-411行）同步修复

### 1.2 代码变更

| 位置 | 变更 |
|------|------|
| Phase 2 可见性恢复 (~L397-411) | 4 处 VarSet 位运算 → If+算术 |
| Phase 3 文件夹状态设置 (~L532-560) | 两阶段合并为单阶段 + 5 处位运算 → If+算术 |

---

## 二、ZScript 兼容性关键发现

| 上下文 | `&` (AND) | `|` (OR) | 结论 |
|--------|-----------|----------|------|
| `[If,(a & N) == N,...]` | 可用 | N/A | 条件判断中安全 |
| `[VarSet,x,x & N]` | **不可靠** | N/A | 赋值中可能返回 0 |
| `[VarSet,x,x \| N]` | N/A | **不可靠** | 赋值中可能返回 0 |
| `[VarSet,x,x + N]` | N/A | N/A | 算术可靠 |

**安全模式**：位操作一律用 If 判断 + 加减运算替代 VarSet 位运算。

---

## 三、测试工具

### ZBridge_folder_test_step1.txt
Dump SubTool States 测试脚本，功能：
- 遍历所有子工具，显示 bit0（容器可见）、bit1（folEye）、bit10（CLOSED）、bit11（OPENED）
- 可加载于 ZPlugin:ZBridge_Test 面板
- 输出格式：`[idx] name\n  FOLDER/TOOL b0=X b1=VIS/HID CLOSED/OPENED`

### ZBridge_folder_test_minimal.txt
最小化测试，验证文件能被 ZBrush 加载。

---

## 四、测试结果

| 测试项 | 结果 |
|--------|------|
| TOOL bit0 保留 | 通过（导入后 b0=1） |
| FOLDER bit0 保留 | 通过（导入后 b0=1） |
| FOLDER bit1 可见 | **通过**（b1=VIS 正确保留） |
| FOLDER bit1 隐藏 | **通过**（b1=HID 正确保留） |
| FOLDER bit10 CLOSED | 通过 |
| FOLDER bit11 OPENED | 通过 |

---

## 版本：0.4.0 回退 — 全面取消 .zbridge 打包功能
## 日期：2026-07-21
## 状态：已完成

---

## 一、回退原因

.zbridge 单文件打包方案存在以下根本性问题，决定全面回退：

1. **C++ EXE 异步调用不可靠**：`ShellExecute` 在 ZBrush 中异步执行，ZScript 无法获取进程退出码或同步等待，只能通过轮询文件存在性（`[FileExists]` + `[Loop,60000]`）检测完成，导致竞态条件和不稳定行为。
2. **PowerShell/C++ 双依赖**：0.5.0 用 PowerShell（Mac 不可用），0.6.0 换 C++ EXE（需编译、跨平台困难），两者都引入额外部署负担。
3. **临时目录管理复杂**：prepare/unpack/cleanup 三步异步流程，临时目录泄漏风险高。
4. **GoZ 文件夹方案已足够**：原始 0.4.0 的"目录 + GoZ 文件 + manifest"方案功能完整、零外部依赖，打包成 ZIP 可由用户自行完成。

## 二、回退内容

### 2.1 ZBridge.txt 变更

| 变更项 | 0.6.0 → 0.4.0 |
|--------|---------------|
| 版本号 | 0.6.0 → 0.4.0 |
| 移除变量 | `zbZbridgePath`, `zbMeshDir`, `zbExtractDir`, `zbResultPath`, `zbExportRoot`, `zbConfigPath`, `zbWaitCount`, `zbManFound`, `zbMeshName`, `zbShellMem` |
| 导出文件选择 | `.zbridge` → `.goz`（`FileNameAsk,"GoZ(*.goz)\|*.goz\|\|"`） |
| 导出 GoZ 命名 | `Meshes/SubTool_N.goz` → `{subtoolName}.goz`（子工具原名） |
| 导出后处理 | `ShellExecute` + 轮询 pack → 直接完成（无后续步骤） |
| 导入文件选择 | `.zbridge` → `.goz` |
| 导入前处理 | `ShellExecute` unpack + 轮询 manifest → 直接读取 manifest |
| 导入 GoZ 路径 | `Meshes/SubTool_N.goz` → `{subtoolName}.goz` |
| 导入后清理 | `ShellExecute` cleanup → 无（无需清理） |
| DLL 加载位置 | `ZBGetSysInfo` → `ZBRunImport`（回归 0.4.0 位置） |
| 按钮描述 | "Export to .zbridge package" → "Export to GoZ files" |

### 2.2 删除的文件

| 文件 | 说明 |
|------|------|
| `src/packer/ZBridgePacker.cpp` | C++ 打包/解包源码 |
| `src/tools/ZBridgePacker.exe` | 编译后的打包 EXE |
| `src/tools/zb_pack.ps1` | PowerShell 打包脚本（0.5.0 方案） |
| `src/tools/zb_pack_launcher.bat` | PowerShell 启动器 |
| `src/packer/` | 空目录已删除 |
| `src/tools/` | 空目录已删除 |
| `tests/test_zbridge_integration.ps1` | 打包集成测试 |
| `tests/test_zbridge_packer.ps1` | 打包单元测试 |

### 2.3 保留的 release 存档

`releases/0.5.0/` 和 `releases/0.6.0/` 作为历史存档保留，不删除。其中包含打包相关文件（`ZBridgePacker.exe`、`zb_pack.ps1` 等），供后续参考。

> **版本号重计说明（2026-07-31）**：上述历史 0.5.0/0.6.0 存档实际未保留在 `releases/` 目录中（目录中仅 0.1.0–0.4.0）。新功能基线从 0.4.0 起重新编号，**新 0.5.0 指"子工具重名检查"**，与历史 0.5.0/0.6.0（.zbridge 打包）含义不同，请勿混淆。

## 三、后续开发注意事项

如需重新引入单文件打包，建议考虑以下方向：

1. **ZScript 原生 ZIP**：调查 ZBrush 是否有内置 ZIP 支持（如 `[ZipCreate]`、`[ZipExtract]`）
2. **同步外部进程**：使用 `[FileExecute]` 代替 `ShellExecute`，或通过文件锁/信号文件实现可靠同步
3. **用户自行打包**：在 UI 中提示用户可将导出目录手动打包为 ZIP
4. **ZBrush 原生格式**：考虑 ZBrush 是否有原生项目打包格式可用

---

## 版本：0.5.0 — 子工具重名检查（功能一，design_next.md）
## 日期：2026-07-31
## 状态：已完成

---

## 一、功能

### 1.1 子工具重名检查（`ZBRunDupCheck`）

在 Export 流程开始处（确认对话框之后、任何文件写出之前）调用：

1. **Pass 1 收集名称**：遍历全部 SubTool，`[IGetTitle,Tool:Item Info]` 取名称并去尾 2 字符（与 manifest name 字段完全一致），null-terminated 写入临时内存块 `ZBDupMem`。
2. **Pass 2 两两比对**：O(n²)，外层 `zbDupI` + 内层 `zbDupJ`，按偏移读取名称；相等判定 = 长度相同 && `[StrFind]` 返回 0（前缀匹配）——规避 ZScript 字符串 `==` 不可靠问题。
3. **命中即中止**：`zbDupFound=1` → 恢复原活动 SubTool → `[Note]` 列出重名名称（去重、带计数）→ `[Exit]`，不写出任何文件。

### 1.2 版本号

- 头注释 `//Version: 0.5.0`，About 按钮文案更新为 `ZBridge v0.5.0`。

### 1.3 编码

- 源文件与发布文件均修复为 UTF-8 BOM + CRLF（`fix_encoding.ps1`），`check_zs.ps1` 验证括号平衡 591/591。

---

## 二、代码变更

| 文件 | 变更 |
|------|------|
| `src/zscript/ZBridge.txt` | v0.5.0；+14 个 `zbDup*` 全局变量；+`ZBRunDupCheck` 例程（~60 行）；Export 流程接入调用（L131-136） |
| `releases/0.5.0/ZBridge/ZBridge.txt` | 同上 |
| `releases/0.5.0/ZBridge/ZBridgeData/` | 拷贝自 0.4.0（ZFileUtils64.dll / ZFileUtils.lib） |

## 三、测试计划

| 测试项 | 通过标准 |
|--------|---------|
| 无重名回归 | 正常导出，不受影响 |
| 单对重名 | 导出中止，Note 列出该名称 |
| 多个重名 | 全部列出且去重、计数正确 |
| 重名子工具已改名后重导 | 正常导出 |

### 0.5.0 修复（2026-07-31）

- **重名提示窗口自动消失**：`[Note]` 第 3 参数为 Display Duration（秒），原写法 `[Note,zbNoteText,,1,4737096,,400]` 中 `1` 导致 1 秒后自动关闭。改为第 3 参数留空（默认 0 = 等待用户点击），必须点击 Close 按钮才消失。
- **全面检查所有 Note**：共 10 处，其中 3 处确认框（Proceed/Cancel、Import/Cancel）本就用第 3 参数为空，无问题；其余 7 处（No Tool loaded、No SubTools found、Export Complete、Manifest not found、Manifest is empty、Import Complete、About）均带 `,,1,4737096,`（1 秒自动消失），已全部改为 `,,,4737096,`（等待点击）。所有 Note 前均有 `NoteIButton`，改为等待点击不会导致窗口无法关闭。

## 四、说明

- Import 侧不检查（导出入口已保证唯一）。
- 后续功能（动态细分 / 图层 / 贴图）均依赖本检查保证 `<名>.goz`、`Layers/<名>/`、`Textures/<名>_TXTR.tif` 关联唯一。

---

## 版本：0.6.0 — 动态细分预览与属性还原（功能二，design_next.md）
## 日期：2026-07-31
## 状态：已完成

---

## 一、功能

### 1.1 动态细分 8 属性保存/还原

| # | 属性 | UI 路径 | ext 键 | 类型 |
|---|------|---------|--------|------|
| 1 | Dynamic 按钮 | `Tool:Geometry:s.Dynamic` | `dynActive` | 0/1 |
| 2 | FlatSubdiv | `Tool:Geometry:s.FlatSubdiv` | `dynFlat` | int |
| 3 | SmoothSubdiv | `Tool:Geometry:s.SmoothSubdiv` | `dynSmooth` | int |
| 4 | Thickness | `Tool:Geometry:s.Thickness` | `dynThick` | float |
| 5 | Segments | `Tool:Geometry:s.Segments` | `dynSegs` | int |
| 6 | Post SubDiv | `Tool:Geometry:s.Post SubDiv` | `dynPost` | 0/1 |
| 7 | Offset | `Tool:Geometry:s.Offset` | `dynOffset` | float |
| 8 | Smoothness | `Tool:Geometry:s.Smoothness` | `dynSmoothness` | float |

- 存储位置：manifest **ext 扩展字段**（第 10 个 pipe 字段），`key=value;` 串联，如 `dynActive=1;dynFlat=0;dynSmooth=2;dynThick=0.5;...`。
- **Export**（`ZBRunDynRead`）：逐项 `[IExists]` 判空读取（低版本无该属性则键不写入）→ 拼 ext 串 → 导出 GoZ 前若 Dynamic 为开则 `[IUnPress]` 临时关闭预览（避免预览效果烘焙进 GoZ 几何）→ `ZBRunDynRestorePreview` 在导出后按原值恢复。
- **Import**（`ZBRunExtParse` + `ZBRunDynRestore`）：放在 Subdivision 恢复（Reconstruct Subdiv）**之后**，避免被重建细分重置；逐项 `[IExists]` 判空，按钮用 `[IPress]/[IUnPress]`、滑杆用 `[ISet]`，缺失键取默认值 0/0.0。
- 所有 UI 路径读写在 `s.*` 子调色板（与 `P./B./D./a./m.` 同级），UI 路径依据 `zscript_python_reference.md` §1.1（commands.xml 权威定义）。

### 1.2 执行顺序要点（与其他功能无冲突）

- **Export 每个 SubTool 内**：读 colorize/sdiv → SDiv 置最高 → `ZBRunDynRead`（读 8 属性+拼 ext+关预览）→ 构建 manifest（9 字段 + `|ext`）→ `Tool:Export` → 恢复 SDiv → 恢复 Dynamic 预览。
- **Import Phase 1**：名称提取改为"遇到 `zbPipePos9` 即止"（`name|ext` 分隔），旧 manifest 无 ext 字段（pos9=-1）回退原公式，行为零变化。
- **Import Phase 2 每个 SubTool 内**：Colorize → SubDiv（Reconstruct + SDiv）→ Visibility → **DynRestore**（最后执行）。
- **向后兼容**：旧 manifest 无 ext 字段 → `zbPipePos9=-1` → 跳过动态细分恢复；ext 内缺某键 → 该项取默认。低版本 ZBrush 缺路径 → `[IExists]` 跳过不报错。

## 二、代码变更

| 文件 | 变更 |
|------|------|
| `src/zscript/ZBridge.txt` | v0.6.0；+15 个全局变量（dynActive/dynFlat/dynSmooth/dynThick/dynSegs/dynPost/dynOffset/dynSmoothness/zbExtStr/zbExtKey/zbExtVal/zbExtPos/zbExtEnd/zbExtFound/zbPipePos9）；+4 个例程（`ZBRunDynRead`/`ZBRunDynRestorePreview`/`ZBRunExtParse`/`ZBRunDynRestore`，约 165 行）；Export 循环接入（读属性+关预览+ext 写入+恢复预览）；`ZBRunManParse` 增加 pos9；Import Phase1 名称提取兼容 ext、Phase2 末尾接入 `ZBRunDynRestore`；About/头注释更新 |
| `releases/0.6.0/ZBridge/ZBridge.txt` | 同上 |
| `releases/0.6.0/ZBridge/ZBridgeData/` | 拷贝自 0.5.0（ZFileUtils64.dll / ZFileUtils.lib） |
| `doc/ZBridge.md` / `doc/design_next.md` | 功能二标记 ✅ 0.6.0 已完成 |

## 三、测试计划

| 测试项 | 通过标准 |
|--------|---------|
| 8 属性 UI 路径在两个 ZBrush 版本 `[IExists]` + `[IGet]/[ISet]` 往返 | 全部路径存在且读写一致 |
| Dynamic=开 的 SubTool 导出 → 导入 | 预览关闭导出（几何不含预览效果）、导出后恢复开、导入后还原开 |
| 滑杆值非默认（如 Thickness=0.5、Smoothness=0.8）往返 | ext 字符串数值一致，导入后 `[IGet]` 复核一致 |
| 旧 manifest（无 ext 字段）导入回归 | 名称/Colorize/SubDiv/Visibility 行为与 0.5.0 完全一致 |
| 低版本 ZBrush 缺部分属性 | 缺失键跳过不报错，导入完成 |
| 与重名检查/Folder/可见性合并 | 全量往返正常 |

## 四、说明

- float 值以字符串原样存取（`Val`/`StrMerge`），不额外定精度。
- 按钮型（Dynamic/Post SubDiv）用 `[IPress]/[IUnPress]`，滑杆型用 `[ISet]`；`dynActive` 在导入时最先设置（使滑杆可用，后续 `ISet` 生效）。
- 待实测项（`zscript_python_reference.md` §八）：滑杆数值范围、关闭预览导出后几何形态、Dynamic 按钮在低版本的按钮语义。

---

## 五、0.6.0 UI 更新（2026-07-31）

### 5.1 按钮重命名

| 原名 | 新名 |
|------|------|
| Export For Older Version | Export |
| Import From Newer Version | Import |

### 5.2 About 弹窗精简

```
ZBridge v0.6.0
+ Cross-Version Tool Migration
Subtool, Subdivision, Dynamic, Folder, Visibility
ZBrush Version: <ZVers>
Platform: <zbPlatformStr>
Author: Aniraiden
```

- 主功能一句 `+ Cross-Version Tool Migration`，核心功能关键词单行列出（不换行）
- 保留版本号、ZB 版本、平台，末尾加作者 Aniraiden

### 5.3 关键发现：Note 窗口高度有限

- **表现**：About 内容 13 行时底部被截断（显示到 `Platform:` 一半），宽度调大（250→320）无法解决
- **结论**：Note 窗口高度约限制 12 行，超长内容需精简行数（现 6 行，必定完整显示）
- **经验**：Note 中多行文本务必控制行数 ≤ 11 行，靠减少行数而非加宽窗口

### 5.4 同步

- `src/zscript/ZBridge.txt` 与 `releases/0.6.0/ZBridge/ZBridge.txt` 保持一致（已拷贝覆盖）

---
## 版本：0.7.0 — 颜色贴图还原 / 贴图重新贴回（功能四，design_next.md）
## 日期：2026-07-31
## 状态：已完成

---

## 一、功能

### 1.1 颜色贴图显式重绑（`ZBRunTexDetect` / `ZBRunTexVerify` / `ZBRunTexExtAppend` / `ZBRunTexRestore`）

GoZ 文件不嵌入图像数据，仅含 `GoZ_TAG_TEXTURE_MAP_PATH` 路径字符串块；贴图本体是 `Tool:Export` 时 ZBrush 自动写到 .goz 旁边的独立 `.tif`（GoZ 命名约定：颜色 `_TXTR.tif`、法线 `_NM.tif`、置换 `_DM.tif`）。本版本走**显式重绑**，不依赖 ZBrush 导入时的隐式路径解析。

**Manifest ext 新增键**（design_next.md §6.3）：

| 键 | 类型 | 说明 |
|----|------|------|
| `hasTexture` | 0/1 | 子工具是否绑定颜色贴图 |
| `textureFile` | string | 贴图相对路径，如 `Body_TXTR.tif` |

- **Export**：
  - `ZBRunTexDetect`（`ZBRunDynRead` 之后、导出之前）：`[IGetTitle,Tool:Texture Map:TextureMap]` 非空 → `hasTexture=1`；同时删除上次导出残留的 `<名>_TXTR.tif`，保证导出后 `[FileExists]` 只反映本次导出。
  - `Tool:Export` 导出 goz 后，ZBrush 自动在同目录写出 `<子工具名>_TXTR.tif`（goz 文件名即子工具名，命名约定 `<gozBase>_TXTR.tif`）。
  - `ZBRunTexVerify`（导出后）：`[FileExists]` 确认实际文件，记录 `zbTexFile`。
  - `ZBRunTexExtAppend`：把 `hasTexture=1;textureFile=<文件>;` 追加进 ext 扩展字段（未找到贴图文件则不写键，导入取默认 0/空）。
  - **manifest 写入时机调整**：从"导出前"移到"导出后"（先导出 → 确认贴图文件名 → 再拼 manifest 记录），保证 textureFile 是实际生成的文件名。
- **Import（Phase 2 末尾，紧接 `ZBRunDynRestore`）**：`ZBRunTexRestore` 解析 ext 的 `hasTexture=`/`textureFile=` → 拼绝对路径 `[FileExists]` 校验 → `[FileNameSetNext]` + `[IPress,Tool:Texture Map:Import]`（`[IExists]` 判空）→ `[ISet,Tool:Texture Map:Texture On,1]`。文件缺失计入 `zbImportErrors`。

### 1.2 版本号

- 头注释 `//Version: 0.7.0`，About 按钮文案更新为 `ZBridge v0.7.0`（核心功能关键词新增 Texture），IButton UI 版本 0.6→0.7。

## 二、代码变更

| 文件 | 变更 |
|------|------|
| `src/zscript/ZBridge.txt` | v0.7.0；+5 个全局变量（zbTexTitle/zbHasTexture/zbTexFile/zbTexPath/zbTexFound）；+4 个例程（ZBRunTexDetect/ZBRunTexVerify/ZBRunTexExtAppend/ZBRunTexRestore，约 90 行）；Export 循环重构（manifest 写入移到导出后 + 3 处接入贴图例程）；Phase 2 末尾接入 ZBRunTexRestore；About/头注释更新 |
| `releases/0.7.0/ZBridge/ZBridge.txt` | 同上（与 src 字节一致，UTF-8 BOM + CRLF，括号 872/872） |
| `releases/0.7.0/ZBridge/ZBridgeData/` | 拷贝自 0.6.0（ZFileUtils64.dll / ZFileUtils.lib） |
| `doc/ZBridge.md` / `doc/design_next.md` | 功能四标记 ✅ 0.7.0 已完成 |

## 三、测试计划

| 测试项 | 通过标准 |
|--------|---------|
| 导出贴图文件名约定实测 | 带贴图 SubTool 导出后确认 `<子工具名>_TXTR.tif` 生成（基于 goz 文件名；若实测为其它命名基准需调整 `ZBRunTexVerify`） |
| 无贴图回归 | manifest 无 hasTexture/textureFile 键，导入行为与 0.6.0 一致 |
| 单 SubTool 带贴图导出→导入 | Texture 槽绑定 + Texture On=1 恢复 |
| 多 SubTool 部分带贴图 | 仅带贴图的条目重绑，其余不受影响 |
| 旧 manifest（无 ext）导入回归 | 名称/Colorize/SubDiv/Visibility/Dynamic 行为与 0.6.0 一致 |
| 低版本 ZBrush 缺 `Tool:Texture Map:Import` | `[IExists]` 判空跳过，不报错 |
| 贴图克隆行为 | `Tool:Texture Map:Import` 是否自动绑定当前 Tool 槽（design_next §5.6 验证点 2/3） |

## 四、说明

- **文件重命名限制**：ZScript 无文件重命名/移动命令（ZFileUtils 只重命名 UI 条目），无目录列举命令，故贴图保留在导出根目录（与 goz 平级），`textureFile` 记录实际文件名（design_next.md §5.3 兜底方案），不强行移入 `Textures/` 子目录。
- **Texture On 强制置 1**：按 design_next.md §5.4，导入后 `Texture On=1`（未保存/还原开关状态）。
- 待实测项：`Tool:Texture Map:Import` 路径 `[IExists]` 有效性、自动绑定行为、贴图克隆行为、Texture On 往返（design_next.md §5.6）。

### 0.7.1 修订（2026-07-31）：贴图导入报错修复

**现象**：导入时弹出 "Error encountered while importing a file"。

**排查结论**：
- 路径拼接正确：`zbImportDir`（`[FileNameExtract,zbInputFile,1]`）与 Phase 1 goz 导入一致，`[FileExists,zbTexPath]` 已通过（否则不会进入导入），排除路径/文件缺失。
- 错误只可能来自 `[IPress,Tool:Texture Map:Import]`：该路径"不在 commands.xml 静态定义"，其脚本化文件对话框在部分版本不消费 `[FileNameSetNext]` 预设，对话框以取消关闭 → ZBrush 弹通用导入错误。
- 参考文档本就记录备选方案：全局 `Texture:Import`（trans=1119）是脚本化导入的稳定路径。

**修复**（`ZBRunTexRestore`）：改为 `[FileNameSetNext] + [IPress,Texture:Import]`（导入 Texture 面板）→ `[IPress,Tool:Texture Map:Clone Txtr]`（克隆当前纹理到 Tool 槽）→ `[ISet,Tool:Texture Map:Texture On,1]`。`Texture:Import` 缺失计入 `zbImportErrors`。不再使用 `Tool:Texture Map:Import`。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 876/876，UTF-8 BOM + CRLF）。

### 0.7.2 修订（2026-07-31）：贴图未绑定 Tool 槽 + 垂直翻转

**现象**：
1. 改用 `Texture:Import` + `Clone Txtr` 后，贴图导入到 Texture 面板成功，但**没有贴到 Tool 的 TextureMap 槽**（`Tool:Texture Map:Clone Txtr` 未生效/未绑定）。
2. 贴图导入后**垂直方向翻转**（ZBrush 长期通病，导入贴图需运行一次 Flip Vertically）。

**修复**（`ZBRunTexRestore`）：
1. **主路径恢复为 `Tool:Texture Map:Import`**（直接绑定 Tool 槽，符合用户要求优先使用 Tool 内 TextureMap 导入）。部分版本该按钮的脚本化文件对话框未消费 `FileNameSetNext` 预设（弹 "Error encountered while importing a file" 且不绑定），故通过 `[IGetTitle,Tool:Texture Map:TextureMap]` 验证绑定结果：
   - 绑定成功 → 完成；
   - 未绑定 → 备选 `Texture:Import` + `Tool:Texture Map:Clone Txtr`（兜底）。
2. **Flip Vertically**：导入后运行 `Tool:Texture Map:Flip Vertically`（备选路径 `Tool:Texture Map:Flip Vertical`，均 `[IExists]` 判空）。
3. 保留 `Texture On=1`。

**验证点**（需实测）：`Tool:Texture Map:Import` 是否弹 "Error encountered" 框；绑定验证是否通过；`Tool:Texture Map:Flip Vertically` 路径 `[IExists]` 是否命中；翻转后贴图方向是否正确。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 892/892，UTF-8 BOM + CRLF）。

### 0.7.3 修订（2026-07-31）：导入路径实测为 File:Texture:Import

**现象**：0.7.2 仍弹 "Error encountered"。用户查看按钮提示，确认 Texture 面板导入按钮的实际路径是 **`File:Texture:Import`**（而非参考文档记录的 `Texture:Import`）。用户手动执行 `File:Texture:Import` 后：子工具**自动贴上**最新导入的贴图（自动绑定 Tool 槽，无需 Clone Txtr），但贴图**垂直翻转**。

**修复**（`ZBRunTexRestore`）：
1. **主路径改为 `[FileNameSetNext] + [IPress,File:Texture:Import]`**（实测按钮路径，导入后自动绑定 Tool 槽）。移除 `Tool:Texture Map:Import`（实测必弹 "Error encountered..."）。
2. 保留 `Texture:Import` 作为老版本兜底路径（`[IExists]` 判空）。
3. 保留绑定验证（`[IGetTitle,Tool:Texture Map:TextureMap]`）+ `Clone Txtr` 兜底。
4. 垂直翻转：保留 `Tool:Texture Map:Flip Vertically`（备选 `Flip Vertical`），待实测确认路径。

**验证点**（需实测）：
- `[IExists,File:Texture:Import]` 是否命中（应为 1）；导入不再弹错。
- 导入后贴图是否自动绑定 Tool 槽（验证通过则不走 Clone）。
- Flip 按钮：`Tool:Texture Map:Flip Vertically` / `Flip Vertical` 哪个命中；若均未命中，请查看 Tool > Texture Map 面板 Flip 按钮提示文本。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 892/892，UTF-8 BOM + CRLF）。

### 0.7.4 修订（2026-08-01）：贴图未贴到子工具 + 未垂直翻转（根因修正）

**现象**：不再弹错、贴图正确导入 Texture 面板，但**未贴到子工具的 TextureMap 槽**，且**未垂直翻转**。

**排查结论（推翻 0.7.1-0.7.3 的部分假设）**：
1. **`Clone Txtr` 方向是 tool→palette，不是 palette→tool**。官方文档原文："Duplicates the current texture and adds it to the Texture palette as the active texture."（Tool > Texture Map 子面板）。因此它**永远无法**把面板纹理绑定到 Tool 槽——之前把它当"绑定兜底"从根上就是错的。
2. **Flip V 按钮在 Texture 面板，脚本路径为 `Texture:Flpv`**（ZBrushCentral 2022 年录制脚本实证 `[IPress,Texture:Flpv]`；按钮显示 "Flpv"/"Flip V (vertically)"）。此前使用的 `Tool:Texture Map:Flip Vertically`/`Flip Vertical` 路径不存在（`[IExists]` 恒 0），Flip 从未执行。
3. **`File:Texture:Import` 在脚本模式下不自动绑定 Tool 槽**（手动模式会自动贴；脚本模式不会）。且导入是**异步**的——旧代码导入后立即读 `IGetTitle(TextureMap)`，读到的是导入前的空值，触发无用的 Clone Txtr。

**修复**（`ZBRunTexRestore` 重写，ZBrushCentral marcus_civis 规范化脚本）：
1. 导入前记录面板纹理数 `[IGetMax,Texture:Item Info]`。
2. `File:Texture:Import` 导入（`Texture:Import` 兜底）。
3. **等待异步导入完成**：`[Loop,3000,[If,[IGetMax,Texture:Item Info] > zbTexCount,[LoopExit]] [Delay,0.1]]`。
4. `[ISet,Texture:Item Info,[IGetMax,Texture:Item Info]]` 选中刚导入的纹理（最后一个），读标题 `Texture:Current Texture`（兜底 `Texture:Item Info` + 去尾 2 字符）。
5. **翻转**：`[IPress,Texture:Flpv]`（兜底 `Texture:FlipV`/`Texture:Flip Vertically`）。
6. **绑定**：`[IPress,Tool:Texture Map:TextureMap]` 打开拾取器 → `[IPress,[StrMerge,"PopUp:",[Var,zbTexTitle]]]` 点击该纹理（规范化脚本）。
7. **绑定验证 + 重试一次**：`[IGetTitle,Tool:Texture Map:TextureMap]` 为空则再执行一次拾取器点击（ZBrush 脚本已知怪癖：首次常不生效，第二次生效）。
8. `Texture On=1`。

**新增全局变量**：`zbTexCount`（导入前面板纹理数）、`zbTexCheck`（绑定验证）。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 938/938，UTF-8 BOM + CRLF，36617 字节）。

**验证点**（需实测）：
- 导入后子工具 TextureMap 槽是否已贴上贴图（Tool > Texture Map 显示纹理名）。
- 贴图方向是否正确（不再上下颠倒）。
- 若 Flip 未生效：请查看 Texture 面板 Flip 按钮提示文本，确认脚本路径是否为 `Texture:Flpv`。
- 若拾取器 PopUp 未命中（面板纹理名与读取标题不一致）：把 Texture 面板当前纹理的标题/名称反馈出来。

### 0.7.5 修订（2026-08-01）：绑定落在 Texture 面板而非 Tool 槽

**现象**：贴图正确导入、正确翻转、弹窗正确弹出，但绑定落在**左侧工具栏的 Texture 面板**（成为活动面板纹理），Tool 的 TextureMap 槽未被赋值。

**排查结论**：
1. **拾取器 PopUp 点击只选中面板纹理，不提交到 Tool 槽**。ZBrush 录制脚本（ZBrushCentral rbrose 2022）显示**手动绑定**的真实行为是：`[IPress,Texture:<纹理名>]`（在 Texture 面板列表按下该条目，触发"自动贴到当前子工具"）+ `[IPress,Tool:Texture Map:TextureMap]`。单纯 `ISet,Texture:Item Info` 选中 + `PopUp` 点击在脚本下仅设置面板活动纹理。
2. **ZBrush 已知怪癖**：该绑定流程"首次运行不生效，第二次运行生效"（rbrose 2022 实测；marcus_civis 证实）。因此必须重试。

**修复**（绑定步骤重写）：
- 每次尝试顺序：`[IPress,Texture:<名>]`（面板列表按下，模拟手动选择触发自动贴）→ `[IPress,Tool:Texture Map:TextureMap]` → `[IPress,PopUp:<名>]`（拾取器补充）。
- `[Loop,3]` 最多尝试 3 次，每次用 `[IGetTitle,Tool:Texture Map:TextureMap]` 验证，成功即跳过后续。
- 保留 0.7.4 的异步等待、选中最后纹理、`Texture:Flpv` 翻转逻辑。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 942/942，UTF-8 BOM + CRLF，37198 字节）。

**验证点**（需实测）：
- Tool > Texture Map 槽是否显示纹理名（不再只是左侧工具栏 Texture 高亮）。
- 若仍未绑定：确认 `Texture:<纹理名>` 路径是否命中（可查看录制脚本中按下面板纹理条目的格式），并把 Texture 面板当前纹理名称反馈给我。

### 0.7.6 修订（2026-08-01）：绑定前显式重选子工具 + PopUp 改用 IClick 提交

**现象**：0.7.5 后用户确认"弹出菜单确实是 Tool 的 TextureMap"，但 Tool 槽**仍未载入**贴图。用户提出假设：可能绑定操作时**目标子工具未处于选中状态**（Tool 贴图槽是每子工具一份，赋值必须落到当前选中子工具）。

**排查结论**：
1. 0.7.5 的绑定步骤虽然处于 Phase 2 循环内（循环开头已 `[SubToolSelect,zbIdx]`），但绑定前经过 Colorize/SubDiv/Visibility 恢复，且 ZBrush 脚本环境下子工具选中态可能因中间操作漂移；显式重选能确保拾取器赋值落到正确子工具。
2. 2015 官方规范（ZScript/IconCommand 文档）表明：**工具贴图槽（Tool:Texture Map:TextureMap）的拾取器提交应使用 `IClick`**（点击项目内坐标），`IPress` 仅按压按钮。此前用 `IPress,PopUp:<名>` 可能只"按"未"选"。

**修复**（绑定步骤 0.7.6）：
- 绑定前新增 `[SubToolSelect,zbIdx]`：显式重选目标子工具（与 Phase 2 循环开头的选择一致，重复选择无害）。
- 拾取器提交改为 `[IClick,[StrMerge,"PopUp:",[Var,zbTexTitle]]]`（官方规范：工具贴图槽提交用 IClick），保留 `[IPress,PopUp:<名>]` 作为兜底。
- 保持 0.7.5 的尝试顺序（`Texture:<名>` 按下 → `Tool:Texture Map:TextureMap` → PopUp 点击/按下）与 `[Loop,3]` 重试 + `[IGetTitle]` 验证。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 946/946，UTF-8 BOM + CRLF，37547 字节）。

**验证点**（需实测）：
- Tool > Texture Map 槽是否显示纹理名（重点验证：是否因子工具未选中导致未载入的假设成立）。
- 若仍未绑定：把录制脚本中手动把贴图贴到子工具时的操作序列（或按钮提示文本）反馈给我。

### 0.7.7 修订（2026-08-01）：修复 PopUp 已关闭后的误报错

**现象**：0.7.6 后**贴图正确绑定**到 Tool 槽（用户确认"贴图正确的贴上了"），但弹出错误提示：

```
ZScript Note: Interface item could not be found.
SCRIPT:ZBridge.txt
ERROR: PopUp:shoulderGuard TxTR
IN: [IPress,[StrMerge,"PopUp:",[Var,zbTexTitle]]]
```

**根因**：`IClick,PopUp:<名>`（0.7.6 改为官方规范的提交方式）执行成功后**拾取器随即关闭**，紧随其后的兜底 `IPress,PopUp:<名>` 因 PopUp 项已不存在而报错。绑定已生效，错误仅是弹窗噪音，但会打断/惊吓用户。

**修复**（0.7.7）：
- 将 `IClick,PopUp:<名>` 与兜底 `IPress,PopUp:<名>` **分别用 `[IExists,[StrMerge,"PopUp:",...]]` 判空包裹**。
- 实测逻辑链：IClick 提交成功 → 拾取器关闭 → 第二个 `IExists` 返回 0 → IPress 自动跳过，不再报错。
- 若 IClick 未生效（拾取器仍开着）→ IPress 兜底照常执行，双保险。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 954/954，UTF-8 BOM + CRLF，37980 字节）。

**验证点**（需实测）：
- 导入过程不再弹 "Interface item could not be found" 错误。
- Tool > Texture Map 槽绑定仍生效、贴图方向正确。

### 0.7.8 修订（2026-08-01）：清理遗留选中操作 + 完成后面板当前纹理置空

**现象**：0.7.7 后功能完美（绑定+翻转+无报错），但用户观察到左侧 Texture 面板仍载入贴图，要求移除遗留代码，并在所有贴图载入完成后将面板载入空对象。

**排查结论**：
1. 面板"载入"贴图有 3 个来源：① `File:Texture:Import` 导入（**必须**——拾取器绑定从面板选纹理，手动操作同样如此）；② `[ISet,Texture:Item Info,...]` 显式选中（**遗留 0.7.4**——导入后纹理自动成为面板当前纹理，冗余）；③ `[IPress,Texture:<名>]` 按下面板条目（0.7.5 为模拟手动绑定加入，与 `SubToolSelect+IClick` 共同构成绑定机制，移除有回归风险，**保守保留**）。
2. ZBrushCentral 实证（marcus_civis）：**面板纹理列表无法脚本清空**（仅重启），`Texture:Remove` 按钮仅把当前纹理替换为空白块——这正是"载入空的对象"的可行方式。`Texture:New` 的官方描述是"为 3D 对象创建空白纹理"，可能直接影响 Tool 槽，**不可用**于事后清理。
3. 备选根治方案（远期记录）：marcus_civis 直接导入法 `[IPress,Tool:Texture Map:TextureMap]` → `[FileNameSetNext]` → `[IPress,File:Texture:Import]` → `[IClick,6207]` 可绕过面板列表，但翻转机制未验证，暂不采用。

**修复**（0.7.8）：
- 移除遗留 ②：主分支 `[ISet,Texture:Item Info,[IGetMax,Texture:Item Info]]` 删除（导入后 `Texture:Current Texture` 即刚导入贴图，`zbTexTitle` 读取不受影响）；兜底分支（无 Current Texture 旧版本）保留 ISet。
- 新增 `zbTexImported` 标志（全局变量 + Phase 2 循环前重置；ZBRunTexRestore 进入导入流程置 1），**仅当本次导入确实导入了贴图**才触发清理，避免误删用户原有面板纹理。
- Phase 2 循环结束后统一清理：`[If,zbTexImported == 1,[If,[IExists,Texture:Remove],[IPress,Texture:Remove]]]` —— 将面板当前纹理置空（变空白块）。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 959/959，UTF-8 BOM + CRLF，39152 字节）。

**验证点**（需实测）：
- 左侧 Texture 面板不再残留贴图（当前纹理为空白块）。
- **关键**：面板置空后，各子工具 Tool > Texture Map 槽绑定仍显示贴图（验证 Tool 槽保存的是纹理副本，不受面板 Remove 影响）。
- 贴图方向仍正确、无报错。

### 0.7.9 修订（2026-08-01）：回退 0.7.8 面板清理（绑定静默失败，非 Remove 破坏）

**现象**：0.7.8 实测——贴图正确导入、正确垂直翻转、面板成功置空，但**子工具未贴上贴图**（用户确认：从头到尾没贴上、全部子工具未贴上）。

**根因（用户观察 + 代码时序分析）**："从头到尾没贴上"+"全部子工具"证明**绑定从未成功执行**，Remove 与丢失无关。0.7.8 相比 0.7.7 的唯一绑定相关改动是**移除主分支 `[ISet,Texture:Item Info,...]`**：

- ZBrush 怪癖：导入后内部活动纹理已切换（故 `Texture:Flpv` 翻转"看起来正确"），但 **`Texture:Current Texture` 的标题读取需要 `ISet` 选中后才刷新**。
- 无 ISet 时 `zbTexTitle` 读为空 → 绑定块入口 `[If,[StrLength,zbTexTitle] > 0,` **整个跳过** → 绑定静默失败（无报错）。
- 0.7.7 有 ISet 绑定成功（用户确认完美），0.7.8 无 ISet 全部失败 → **ISet 是绑定成功的前置条件**。

**修复**（0.7.9）：
- **完全回退 0.7.8 的 5 处改动**，恢复到 0.7.7 已验证的完美状态（含恢复主分支 `[ISet,Texture:Item Info,[IGetMax,Texture:Item Info]]`）：
  - 删除全局变量 `zbTexImported`、Phase 2 循环前重置、ZBRunTexRestore 内置位、循环后清理块
- 面板残留贴图：接受为 ZBrush 机制必然——绑定依赖面板纹理存在 + `ISet` 选中读取标题，**面板无法清理**（列表无法脚本清空；Remove 清当前纹理也会悬空 Tool 槽引用，不可用）。

**备选根治方案（远期，需实测）**：marcus_civis（ZBrushCentral 2012）直接导入法——`[IPress,Tool:Texture Map:TextureMap]` → `[FileNameSetNext]` → `[IPress,File:Texture:Import]` → `[IClick,6207]`，在拾取器打开状态导入，纹理直接赋给 Tool 槽**绕过面板列表**。未解决点：直接导入的纹理能否被 `Texture:Flpv` 翻转（若不入面板则无面板当前纹理可翻）。若用户坚持面板不残留，可尝试实现并实测。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 954/954，UTF-8 BOM + CRLF，37980 字节，与 0.7.7 完全一致）。

**验证点**（需实测）：
- 子工具 Tool > Texture Map 槽重新正确贴上贴图（验证 ISet 恢复后绑定恢复正常）。
- 贴图方向正确、无报错。

### 0.7.10 修订（2026-08-01）：保留 ISet 单独验证面板清理（Remove）

**现象**：0.7.9（恢复 ISet）后绑定恢复正常、功能正常，但左侧 Texture 面板又残留贴图（绑定机制的必然结果）。用户仍希望面板载入空对象。

**关键认知修正**：0.7.8"Remove 破坏 Tool 槽绑定"的结论**被 ISet 问题污染**——当时绑定从未成功（zbTexTitle 空、绑定块整体跳过），Remove 对绑定的影响**从未单独验证**。0.7.9 绑定正常后，值得重新单独验证 Remove。

**修复**（0.7.10）：
- **保留 ISet**（0.7.9 已恢复，绑定正常的基础），仅恢复 0.7.8 的面板清理部分：
  - 全局变量 `zbTexImported` + Phase 2 循环前重置 + ZBRunTexRestore 内置位（仅当确实导入过贴图才清理，避免误删用户原有面板纹理）
  - Phase 2 循环结束后 `[If,zbTexImported == 1,[If,[IExists,Texture:Remove],[IPress,Texture:Remove]]]` 清面板当前纹理
- 单一变量验证：若 Tool 槽绑定保持 → Remove 方案成立；若绑定丢失 → 放弃本方案，转 marcus 直接导入法。

**同步**：`src/zscript/ZBridge.txt` 与 `releases/0.7.0/ZBridge/ZBridge.txt` 已同步（字节一致，括号 961/961，UTF-8 BOM + CRLF，38905 字节）。

**验证结果：✅ 通过**（用户确认）——面板当前纹理变空白、各子工具 Tool 槽绑定保持、方向正确、无报错。**贴图重新贴回功能（功能四）完整完成。**

### 成功经验（后续开发直接参考）

1. **ISet 是绑定前置**：`Texture:Current Texture` 标题需 `[ISet,Texture:Item Info,index]` 选中后才刷新。无 ISet → `zbTexTitle` 空 → 绑定块 `[If,zbTexTitle>0]` 整体跳过（**静默失败，无报错**）。
2. **Remove 不破坏绑定**：绑定完成后 `[IPress,Texture:Remove]` 清面板当前纹理（变空白块），**不影响 Tool 槽已绑定贴图**。0.7.8"Remove 破坏"是 ISet 问题污染的误判。
3. **清理需标志保护**：`zbTexImported==1`（本次导入过贴图）才 Remove，避免误删用户原有面板纹理。
4. **绑定完整流程（已验证）**：`File:Texture:Import`（异步）→ 等待面板数量增加 → `ISet` 选中最后 → `Current Texture` 读标题 → `Texture:Flpv` 翻转 → `SubToolSelect` + `Texture:<名>` 按下 + `IClick,PopUp:<名>`（提交）+ `IExists` 判空兜底 `IPress` → `IGetTitle` 验证 `Loop 3` 次重试 → 全部子工具完成后统一 `Remove` 清面板。

---

## 版本：0.8.0 — 雕刻图层还原（功能三，design_next.md §4.8）
## 日期：2026-08-01（T4 首测 2026-08-02）
## 状态：T3 导出侧通过；T4 首测全流程跑通（快照内容 / 导入 k=0 替换两问题待小规模测试修复）

### T3 导出侧（ZBRunLayerSnapshot 系列 6 例程）

**实现要点**：方案 B 平级命名（`<stName>_LayerBase.goz` / `<stName>_Layer<i>.goz` 平级根目录）+ `layers.txt`（null 终止记录 `subtoolName|layerIndex|layerName|intensity|visible|enabled|vertexCount\0`，文件序=栈顶→栈底=layerIndex **降序**）。机制全表见 zscript_python_reference.md §8.5。

**测试场景**：3 子工具混合（layertest02=2 个重名层 LayerA+细分；Cylinder=仅细分；Plane=无层+Dynamic+贴图）。

**闪退排查（DBG 断点二分法，3 轮收窄）**：

| 轮次 | 结论 | 定位 |
|------|------|------|
| 1 | 只见 DBG-A（快照完成）→ 崩 | 崩溃在返回主循环后 |
| 2 | idx=0 全过，idx=1 DBG-5 后崩 | idx=1 `MemWriteString,zbManMem`（0.7.0 稳定功能）→ 堆已被图层代码损坏 |
| 3 | DBG-5b 确认 manWrite 成功 → 仍崩 | `ZBRunLayerDetect` 在空层列表上操作 Scrollbar |

**根因 ×2（均已修复复测通过）**：

1. **`StrExtract` 负长度**：第三参数=**终点索引（含）**，`ZBRunLayerRestoreMem` 误传长度公式 `pipe4-pipe3-1` → 终点<起点 → 堆静默损坏 → 后续 MemWriteString 闪退（另伴随字段错位：强度取成了层名字段）。
2. **空层列表操作 Scrollbar 属未定义行为**：无图层子工具上 `ISet/IGetSecondary(Scrollbar)` 闪退；防护改为先查 `IsEnabled(Layer Intensity)`（无层时滑杆禁用）再碰 Scrollbar，外加 `count<1 ⇒ 0` 钳制。

**验证结果：✅ 通过**——无闪退；重名层由计数法导航正确区分（layerIndex 1/0）；无层子工具正确跳过；导出后源工具层强度/可见性恢复原样；manifest 与 layers.txt 内容正确。

**经验**：

1. ZScript 无调试器 → `[Note,"DBG-x",2]`（2 秒自动消失不阻断）二分定位崩溃阶段，逐轮收窄插入更细断点。
2. 堆损坏型闪退**延迟发作**：崩溃点（manifest MemWriteString）≠ 肇事点（StrExtract 负长度），需沿执行序回溯。
3. 字段解析一律复用已验证模式 `StrExtract(s,pipeK+1,pipeK+1-1)`，勿自造长度公式。
4. "UI 元素存在" ≠ "可安全操作"：空数据状态下的 ISet/IGetSecondary 可能是未定义行为，先用 IsEnabled 类信号判数据存在。

### T4 导入侧（ZBRunLayerImpLoad / ImpMatch / ImpRec / RestoreImport 4 例程）

**顺序定案（用户确认，不可调换）**：细分还原（Phase 2 现有）→ **切最高 SDiv**（快照均在最高 SDiv 导出，顶点一一对齐）→ 逐层**录制导入**还原 → **切回原显示 SDiv**。录制导入只动顶点不动基网格，细分历史保留，无需重跑 Reconstruct。

**形变数学**：录制导入 `delta = 导入网格 − 录制起点网格`；每层建前先全部归零（网格=Base）→ 导入 `B+d_i` → delta=纯层形变；最终 `B + Σd_i×int_i = 原当前态`。

**要点**：主网格=`<stName>_LayerBase.goz`（Phase 1 分支，缺失回退主 goz）；layers.txt 文件序=降序 → **按 layerIndex 值寻记录升序建层**（New 总插栈顶）；退录制先读 `IModGet bit0` 确认再 IClick W-25（防反向误触）；命名走 ZFU RenameSetNext + `Tool:Layers:Rename`（失败降级跳过不中断）；最终 pass 双向恢复可见性（`visCur != 期望 ⇒ IClick W-5`）；单层失败计 `zbImportErrors` 继续。

### T4 首测（2026-08-02）：全流程跑通，暴露导出+导入两侧问题

**测试**：3 子工具混合场景（test22），选 `layertest02.goz` 导入。**DBG 全序列**：`I1 impOk=1 → I2 cnt=2 → I3 k=0 f=1 → I3b 0→1 → I3d rec=1 → I3c li=0 → I3 k=1 f=1 → I3b 0→1 → I3d rec=1 → I3c li=1 → I4 k=1 mod=1 → I2 cnt=0 ×2 → Import Complete (Errors: 2)`。

**✅ 里程碑**：无卡死、无报错、层成功建立（LayerA）；导入侧 4 例程首次全流程走通。

**问题 1（导出侧，T3 遗留未暴露）**：`layertest02_Layer0.goz` 与 `layertest02_Layer1.goz` 形变内容**都是 LayerA 形状**。T3 只验证了 layers.txt 元数据与 goz 导出成功，未验证每层快照的形变内容。根因候选：逐层快照时形变未正确切换（归零失败 / 层切换失效 / ISet 强度后几何未即时应用），需小场景实测裁决。

**问题 2（导入侧）**：k=0 导入走**替换路径**（DBG-I3c `li=0` 层被清 → 层存活检测恢复计数 + Errors++）；k=1 走**更新路径**（`li=1` 层保留、录制导入成功）。两轮差异待查（细分级别状态 / 录制态 / goz 导入后细分保留性）。

**问题 3（结果表现）**：层内无形变 + 最终网格=LayerA 形状 = 快照内容错误（问题 1）+ k=0 替换丢失 Base（问题 2）共同导致。

**卡死排查记录（2026-08-01/02）**：
- probe5 硬编码路径（无 FileNameAsk）→ `Tool:Import` 弹"替换当前工具"确认框（OK/Replace/Yes，扁平样式像 Note）→ 脚本挂起 = 卡死。`IKeyPress 13` 拦不住（异步原生框）。
- `[IPress,Tool:SimpleBrush]` 脚本运行时切换工具 → **同样挂起**（最新版实测 I1 后卡死）→ 移除，恢复裸导入（第 2 次测试验证过的成功路径）。
- 定案：导入必须在**干净 SimpleBrush**（重启后）下运行；ZBrush 导入成功路径 = FileNameAsk 选文件 + 裸 `IPress Tool:Import`。

### 测试计划（单子工具 2 层小规模验证 → 通过后改主程序）

**阶段 0 场景构建**：单子工具 `LayerTest1`，3 级细分；2 层：LayerA（形变 A 明显）+ LayerB（形变 B 明显不同）；强度/可见性各异（A:int1/vis1，B:int0.5/vis0）。

**阶段 1 导出侧验证**：
- 1.1 ZBridge 导出 → 产物齐全（主 goz + `_LayerBase` + `_Layer0` + `_Layer1` + layers.txt）
- 1.2 **快照内容**：逐个导入快照 goz 对比形变——Base=无层形变基准；Layer0=仅 A 形变；Layer1=仅 B 形变（判别：肉眼 + 顶点差 Mesh3DGet）
- 1.3 layers.txt 元数据核对（层名/强度/可见/顺序）

**阶段 2 导入基础**：导入主 goz → 网格/细分级别/显示级别 ✓；无层 ✓

**阶段 3 导入图层还原**：
- 3.1 建层+导入 Layer0 → 层在？网格回 Base？delta 入层？（录制导入 vs 替换路径判别）
- 3.2 建层+导入 Layer1 → 同上
- 3.3 强度/可见性恢复 → 最终=原当前态
- 3.4 细分显示级别=原 curSdiv；3.5 退录制/命名成功

**阶段 4 集成回归**：全部通过 → 改主程序 → 多子工具混合/无层子工具/重名层/旧版兼容（无 layers.txt）回归。

**测试工具**：probe6（单子工具场景，Export + Import 两按钮，路径硬编码测试目录，零文件选择）。
- **probe6 已完成（2026-08-02）**：`tests/ZLayer_probe6.txt`（括号 525/525，UTF-8 BOM + CRLF）
  - 固定目录 `C:/Users/Administrator/Desktop/test22_probe6/`；命名 `probe6_main/LayerBase/Layer0a/Layer1a/Layer0b/Layer1b.goz + layers.txt`（自洽命名，与主程序 `<stName>_` 命名互不影响，机制验证通过后再移植）
  - **Export 按钮**（E0-E7）：E0 导 main 叠加态 → E1 对照枚举（栈底→栈顶，layerIndex 升序写 layers.txt）→ E2 归零（每步记录层名+读回强度）→ E3 导 Base → E4 快照 Pass A（无 Delay，复刻主程序现状，每步记录 置1前/置1后/SelectUp后 层名）→ E5 恢复 → E6 快照 Pass B（ISet 后 Delay300）→ E7 恢复+保存 `probe6_export_log.txt`
  - **Import 按钮**（I1-I5）：I1 导入 Base（记录 SDivMax/层数）→ I2 切最高 SDiv → I3 逐层 New+录制导入 Layer0/Layer1（每步记录 before/after/rec/li/mod，与主程序 RestoreImport 同构）→ I4 恢复强度/可见性 → I5 切回原 SDiv → 保存 `probe6_import_log.txt`
  - **判别逻辑**：Pass A 两文件同形=复刻问题 1，看日志层名区分「SelectUp 导航失效」vs「ISet 后几何未即时应用」；Pass B 正确=需加 Delay；Import 侧 li=0=替换路径复现问题 2

**测试操作步骤（用户）**：
1. 准备/加载单子工具场景：2 层（层名不同，形变明显不同，强度如 1/0.5，可见性一开一关），3 级细分
2. ZScript 面板 Load `tests/ZLayer_probe6.txt` → ZPlugin:ZBridge_Test → **Layer Probe6 Export** → 等 Note 完成
3. 在 ZBrush 中逐个打开 `probe6_Layer0a/Layer1a/Layer0b/Layer1b.goz` 对比形状 → 回报判别数据 + 日志
4. 重启 ZBrush（干净 SimpleBrush）→ Load probe6 → **Layer Probe6 Import** → 等 Note 完成 → 回报 `probe6_import_log.txt` + 最终网格/层状态

**待办**：阶段 0-4 测试 → 修导出侧快照内容（问题 1）→ 修导入侧 k=0 替换（问题 2）→ 集成回归 → 0.8.0 发布收尾。
