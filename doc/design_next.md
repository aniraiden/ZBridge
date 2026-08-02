# ZBridge 新功能设计（基于 0.4.0 基线）

## 〇、基线说明

**开发基线退回 0.4.0**（`releases/0.4.0/ZBridge/ZBridge.txt` → `src/zscript/ZBridge.txt`）。0.4.0 之后的所有版本（0.5.0/0.6.0/0.7.0，含 .zbridge 打包、ZBridgePacker.exe、Dynamic Subdiv 保存等）**全部舍弃，不再参考其实现**。

0.4.0 已具备的能力：

- SubTool 全量导出/导入（GoZ，**以子工具名命名**：`<子工具名>.goz`）
- Manifest 9 字段：`colorize|maxSdiv|curSdiv|subtoolEye|folderEye|isFolder|isOpened|folderName|name\0`
- Folder 结构重建（New Folder + MoveUp + ZFileUtils RenameSetNext）
- 可见性恢复（subtoolEye / folderEye）
- 名称恢复（.dat 文件方法）、Colorize 恢复（在名称恢复之后）
- 细分级别恢复（Reconstruct Subdiv）
- 文件夹工程格式（无打包，Export 选目录、Import 读目录）

在此基线上新增 **4 个功能**：

1. **子工具重名检查**（其他三个功能的前置）
2. **动态细分预览与属性还原**
3. **雕刻图层还原**
4. **颜色贴图还原**

既有硬约束继续有效：ZScript 用 UTF-8 BOM + CRLF；变量 camelCase 无下划线；GoZ 导出用最高细分级别并在导出后恢复原级别；Colorize 在名称恢复之后设置；细分恢复用 Reconstruct Subdiv。

---

## 一、工程目录结构（目标形态）

0.4.0 的导出目录结构扩展为：

```text
ExportFolder/
├── zbridge_manifest.txt          # SubTool 级元数据（9 字段 + 扩展字段）
├── Body.goz                      # 以子工具名命名（0.4.0 现状，goz 与 manifest 同级）
├── Hair.goz
├── ...
├── Textures/                     # 颜色贴图（功能四）
│   ├── Body_TXTR.tif
│   └── ...
└── Layers/                       # 雕刻图层（功能三）
    ├── layers.txt                # 全部图层元数据，null-terminated records
    ├── Body/
    │   ├── Base.goz              # 关闭全部图层影响的基准网格
    │   ├── Layer_0.goz           # 仅激活第 0 层的采样快照
    │   └── Layer_1.goz
    └── Hair/
        ├── Base.goz
        └── Layer_0.goz
```

---

## 二、功能一：子工具重名检查（前置功能）✅ 已实现（0.5.0）

> 状态：0.5.0 已完成。实现为 Export 流程前置例程 `ZBRunDupCheck`，检测到重名即中止并弹窗列出重名名称（等待用户点击关闭）。详见 `development_log.md` 0.5.0 章节。

### 2.1 为什么必须做

0.4.0 的 GoZ 文件以子工具名命名，**同名子工具导出时文件互相覆盖**，后写的覆盖先写的，manifest 中两条记录指向同一文件，导入必错。后续贴图（`Textures/<名>_TXTR.tif`）和图层（`Layers/<名>/`）同样以名称关联，重名会导致数据串扰。

### 2.2 设计

- **时机**：Export 流程开始处，遍历 SubTool 收集名称后、任何文件写出前检查。
- **策略：检测到重名即中止**。弹出 Note 列出重名子工具名称，提示用户先在 ZBrush 中手动改名，再重新导出。
- 不做自动改名：自动改名会引入"导出名 ≠ 原始名"的映射，名称恢复、贴图、图层全链路都要跟着处理映射，复杂度远大于让用户改名。
- Import 侧不检查（导出入口已保证唯一）。

### 2.3 实现要点

- 名称比较用 ZScript 字符串比较，遍历两两比对（SubTool 数量级下 O(n²) 可接受）；或排序后相邻比较。
- 注意 ZBrush 实际允许同名 SubTool 共存，检查必须基于 manifest 记录的 name 字段（即 `[IGetTitle,Tool:Item Info]` 去尾字符后的名字）。

---

## 三、功能二：动态细分预览与属性还原 ✅ 已实现（0.6.0）

> 状态：0.6.0 已完成。实现为 `ZBRunDynRead`（导出侧：读取 8 属性 + 拼 ext 串 + 导出前临时关闭 Dynamic 预览）+ `ZBRunDynRestorePreview`（导出后恢复预览）+ `ZBRunExtParse`/`ZBRunDynRestore`（导入侧：SubDiv 恢复之后逐项还原）。详见 `development_log.md` 0.6.0 章节与 `zscript_python_reference.md`。

### 3.1 目标

保存并还原动态细分的**完整属性集**（8 项，全部位于 `Tool:Geometry` 动态细分区域，精确路径以实测为准）：

| # | 属性 | ext 键名 | 类型 | 说明 |
|---|------|---------|------|------|
| 1 | Dynamic 按钮是否激活 | `dynActive` | 0/1 | 动态细分预览总开关 |
| 2 | FlatSubdiv 级别 | `dynFlat` | int | 平直细分级数 |
| 3 | SmoothSubdiv 级别 | `dynSmooth` | int | 平滑细分级数 |
| 4 | Thickness 级别 | `dynThick` | float | 厚度 |
| 5 | Segments 级别 | `dynSegs` | int | 段数 |
| 6 | Post SubDiv 是否开启 | `dynPost` | 0/1 | Post SubDiv 开关 |
| 7 | Offset 数值 | `dynOffset` | float | 偏移 |
| 8 | Smoothness 数值 | `dynSmoothness` | float | 平滑度 |

存储方式不用 pipe 追加字段，改用 **ext 扩展字段**（key=value 组织），详见第六章。

### 3.2 处理要点

- **Export**：逐项读取并拼入 ext 字符串；导出 GoZ 前临时关闭 Dynamic 预览（避免动态细分效果烘焙进 GoZ 几何），导出后恢复原值。
- **Import**：恢复顺序放在 Subdivision 恢复（Reconstruct Subdiv）**之后**，避免被重建细分重置；逐项 `[IExists]` 判空，低版本无该属性则跳过不报错。
- float 值以字符串原样存取（`Val`/`StrMerge` 转换），不额外定精度。

### 3.3 验证点

- 8 个属性的 UI 路径逐一确认（`[IExists]` + `[IGet]/[ISet]` 探测脚本，两个 ZBrush 版本均实测）。
- Dynamic 按钮开关状态与数值滑杆的读法（按钮用 `[IGet]` 读 0/1，滑杆读数值）。
- 关闭预览导出 GoZ 后几何是否为原始动态细分未应用形态。

---

## 四、功能三：雕刻图层还原（GoZ 快照对比方案）

### 4.1 核心原理

GoZ 不承载 Layer 栈语义，图层数据全部走 ZBridge 自定义存储：

- **每个图层存一个 GoZ 快照**（有几层就存几个），另加一份关闭全部图层的 `Base.goz`。
- C++ 工具对比快照算顶点位移差：`delta_M = Layer_M.vertices - Base.vertices`。
- 导入时把 delta 叠加到导入后的当前网格：`restoreVertices = CurrentBase.vertices + delta_M`，生成临时 `LayerApply_M.goz`。
- ZScript 创建新 Layer → 进入录制 → 导入 `LayerApply_M.goz` → 退出录制，让 ZBrush 自己把差异记录为真实 Layer。

### 4.2 layers.txt 格式

存放于 `Layers/layers.txt`，null-terminated records（与现有 manifest 读取方式一致）：

```text
subtoolName|layerIndex|layerName|intensity|visible|enabled|vertexCount\0
```

示例：

```text
Body|0|Wrinkles|1.0|1|1|245762\0
Body|1|Damage|0.45|1|0|245762\0
Hair|0|ClothFold|1.0|1|1|88420\0
```

- `subtoolName`：关联 `<名>.goz` 与 `Layers/<名>/`（**依赖功能一的重名检查保证唯一**）。
- `layerIndex`：原始图层顺序（导入按此顺序重建）。
- `intensity`：原始强度。采样导出时统一临时设为 **1.0**，保证快照含完整 delta；导入后按原值设置。
- `visible` / `enabled`：图层可见与启用状态。
- `vertexCount`：导入时快速校验拓扑一致性，不一致则跳过该层并报告。
- 快照文件名固定为 `Base.goz` / `Layer_<layerIndex>.goz`，不进 manifest。

### 4.3 Export 流程

对每个含图层的 SubTool（在现有导出循环内扩展）：

1. 切最高细分级别（沿用现有逻辑）。
2. 记录全部图层原始状态（当前层索引、每层 intensity/visible/enabled/录制状态）。
3. 关闭全部图层影响 → 导出 `Layers/<名>/Base.goz`。
4. 逐层：仅激活当前层、intensity 临时设为 1.0 → 导出 `Layer_<i>.goz` → 写 layers.txt 记录。
5. 恢复图层原始状态、SDiv。

### 4.4 Import 流程

在现有恢复链路（名称/Colorize/Subdivision/Visibility）**之后**新增图层恢复阶段：

1. 读取 `Layers/layers.txt`（无此文件则跳过）。
2. 对每个有记录的 SubTool：切最高细分级别。
3. 按 `layerIndex` 顺序逐层：
   - 创建新 Layer。
   - C++ 工具：`delta = Layer_<i>.goz - Base.goz`；`out = 当前导入网格 + delta` → 生成临时 `LayerApply_<i>.goz`。
   - 进入图层录制状态。
   - `FileNameSetNext` + `Tool:Import` 导入 `LayerApply_<i>.goz`。
   - 退出录制。
   - 重命名（参考 ZFileUtils `RenameCurrentLayer`）、设置 intensity/visible/enabled。
4. 恢复原当前 SDiv；清理临时文件。

### 4.5 C++ 工具职责

新增独立小工具（复用 `src/cpp/` 的 GoZ_Mesh 读写代码）：

```text
ZBridgeLayerTool.exe apply <ExportBase.goz> <Layer_i.goz> <CurrentBase.goz> <LayerApply_i.goz>
```

- 读取三个 GoZ 的 POINT_LIST，校验 vertexCount 三者一致。
- 计算并写出 `LayerApply_i.goz`（块顺序遵守 GoZ 写入约定，仅几何相关块即可）。

### 4.6 最大风险与验证点（按优先级）

1. **录制状态下 `Tool:Import` 是否把形变记录进当前 Layer**（而非覆盖 base mesh）——整个方案的生死验证点，必须最先做。
2. 导出侧"仅激活单层"的 ZScript 可控性（Layer 面板 UI 路径待调研：选择层/开关层/设强度）。
3. 顶点数量与顺序一致性：GoZ 往返不变为前提，不一致时跳过并报错。
4. 图层 UI 操作在低版本 ZBrush 的可用性（创建/选择/录制/命名/强度/可见/启用）。

### 4.7 降级方案

若录制导入验证失败：仅恢复图层烘焙后的最终网格（0.4.0 已具备），图层栈不可恢复；或调研 Morph Target 方向（非完整 Layer 语义，仅备选）。

### 4.8 0.8.0 定稿实施方案（2026-08-01 用户确认）

> 状态：**T3 导出侧已实现并通过用户测试（2026-08-01，ZBRunLayerSnapshot 系列例程；3 子工具混合场景、重名层正确区分、无闪退）+ 隔离性审查通过**；**T4 导入侧已实现（2026-08-01，ZBRunLayerImpLoad/ImpMatch/ImpRec/RestoreImport 四例程 + 4 处挂接），待用户测试**。本小节为功能三的定稿设计，经用户逐项确认（范围 / 降级策略 / 恢复机制 / 测试流程精简），实测修正见 §4.8.5。
>
> **T3 调试定案（2 个硬约束，编码必读）**：①`StrExtract` 第三参数 = **终点索引（含）**，误传长度公式 → 终点<起点 → 负长度 → 堆损坏 → 延迟闪退（T3 根因，经 DBG 断点二分定位）；②空层列表上 `ISet/IGetSecondary(Scrollbar)` 属**未定义行为（实测闪退）**，无图层判定必须先查 `[IsEnabled,Tool:Layers:Layer Intensity]`（无层时滑杆禁用）再碰 Scrollbar。
>
> **T4 顺序定案（用户确认，不可调换）**：所有层快照均在最高细分级别导出 → 导入侧**先还原细分级别**（Phase 2 现有 Reconstruct 块）→ **切到最高 SDiv**（顶点一一对齐）→ 逐层录制导入（归零→New→导入→退录制→命名）→ 恢复强度/可见性 → **切回原显示 SDiv**。录制导入只动顶点不动基网格，细分历史保留，**无需重跑 Reconstruct**。

#### 4.8.1 范围与约束（用户确认）

- **还原**：图层名、图层顺序、图层强度（intensity）、图层可见性（eye 图标）。
- **不还原**：图层启用态（enabled）。
- **失败策略**：跳过 + 报告，不中断（复用 `zbImportErrors` 计数，导入完成后统一报告）。
- **恢复机制**：✅ 已实测修正（probe2，见 §4.8.5）——**方案 A（录制导入）复活为唯一路径，无需 DLL**。早期定稿"方案 B（MDD 原生导入）"系 P0 误判方案 A 失败所致，已弃用。
- **测试流程**：精简为 3 阶段 —— ①合并探测脚本 `ZLayer_probe`（1 次运行）→ ②主代码实现 → ③集成测试（1 次往返）。

#### 4.8.2 导出侧流程（在现有导出循环内扩展）✅ T3 已实现

> 快照文件**方案 B（平级命名）**（用户最终选择）：`<stName>_LayerBase.goz` / `<stName>_Layer<i>.goz` 平级放导出根目录，不用子目录。T3 实现位于 `ZBRunLayerSnapshot`（主循环 `ZBRunDynRestorePreview` 后调用）。

```
每个子工具：
  [现有] 取名称/文件夹/Colorize/SDiv → SDiv 置最高 → ZBRunDynRead（读8属性+关预览）
  → ZBRunTexDetect → 导出 <stName>.goz（当前态） → ZBRunTexVerify/ExtAppend → 写 manifest
  → 恢复 SDiv → ZBRunDynRestorePreview
  → 【新增】ZBRunLayerSnapshot：
      无图层（IExists Scrollbar=0 或层数0）→ 整体跳过，行为零变化
      有图层：
        a. 切回最高 SDiv + 临时关 Dynamic 预览（对齐主网格几何）
        b. ZBRunLayerBuildMem：到顶后逐层 SelectDown 枚举，写 layers.txt 记录
           （subtoolName|layerIndex|layerName|intensity|visible|enabled|vertexCount\0，
             layerIndex 0=原始栈底层）
        c. 全部图层强度归零 → 导出 <stName>_LayerBase.goz（基准网格，导入侧主网格）
        d. 逐层 j=0..N（栈底→栈顶）：开眼(IClick W-5) → 强度置1 → 导出 <stName>_Layer<j>.goz
           → 强度置回 0（关键：防止本层影响残留进下一层快照；且自动关眼）
        e. ZBRunLayerRestoreMem：读回记录逐层恢复原强度 + 原可见性（先强度后可见性）
  → 恢复 Dynamic 预览 + SDiv
```

- 图层快照文件命名固定（方案 B 平级）：`<stName>_LayerBase.goz`（基准）、`<stName>_Layer<i>.goz`（i=layerIndex，0=栈底层）。
- 主导入文件：**含图层子工具的导入用 `<stName>_LayerBase.goz`**（基准网格，录制基准天然对齐，多图层无污染）；`<stName>.goz` 保留当前态（无图层子工具照常导入它）。
- 不含图层子工具：完全走现有路径，行为零变化。

#### 4.8.3 layers.txt 格式（独立于主 manifest）

存放于导出根目录 `layers.txt`（方案 B 平级，与快照 goz 同级），null-terminated records（与 manifest 读取方式一致）：

```
subtoolName|layerIndex|layerName|intensity|visible|enabled|vertexCount\0
```

- `subtoolName`：关联 `<name>.goz` 与 `Layers/<name>/`（依赖功能一重名检查保证唯一）。
- `layerIndex`：原始图层顺序（导入按此顺序重建）。
- `intensity`：原始强度。采样导出时统一临时置 1.0（快照含完整 delta），导入后按原值设置。
- `visible`：图层可见性（eye）。
- `enabled`：**记录但不还原**（用户确认）。
- `vertexCount`：拓扑一致性校验字段。方案 B（DLL）在导出侧生成 MDD 时校验；方案 A（纯 ZScript）无法读 GoZ 顶点数，仅记录预留。

#### 4.8.4 导入侧流程（关键：与细分还原的交叉）

```
Phase 2 每子工具现有顺序：Colorize → SubDiv(Reconstruct+SDiv) → Visibility → Dyn → Tex
  → 【新增】ZBRunLayerRestoreImport（Phase 2 末尾，紧跟 Tex）：
    读 layers.txt 匹配当前子工具名；无记录 → 跳过
    有记录：
      a. 循环每层 i（按 layers.txt 的 layerIndex 顺序）：
         ① 已有图层强度全部归零（防御性；保证录制基准 = 基准网格）
         ② [IPress,Tool:Layers:New] 创建新图层（自动进入录制）
         ③ [FileNameSetNext] + [IPress,Tool:Import] 导入 Layers/<name>/Layer_<i>.goz
         ④ 退出录制（IClick REC 图标；或按 P0 实测结果，强度置 0 即退出）
         ⑤ 命名（ZFileUtils ZFU_RenameCurrentLayer）
      b. 【最终状态 pass】逐层导航（SelectDown），每层设置 layers.txt 记录的原强度 + IClick 设可见性
        （关键：若在创建时设强度，后续"全部归零"会把它清零，故强度必须最后统一设置）
      c. 【细分交叉处理】快照导入会清掉细分级别 → 全部图层恢复后，
         重新 Reconstruct Subdiv (maxSdiv-1) 次 + ISet SDiv=curSdiv
```

**细分交叉核心逻辑**：所有快照（基准 + 每层）均在最高 SDiv 导出、顶点一一对齐；录制发生在当前网格上，形变由 ZBrush 自动归到基础层；快照导入破坏细分历史，故**图层恢复之后必须重跑细分恢复**——这是与现有"细分还原"功能的唯一交叉点，其余无冲突。

#### 4.8.5 P0 生死验证 + 合并探测（1 个脚本，1 次运行）

用户手动准备测试工具：一个含 2 个图层的子工具。`ZLayer_probe` 一次运行完成：

| Section | 验证项 | 通过标准 | 失败影响 |
|---------|--------|---------|---------|
| A | P0a：录制中导入形变 GoZ 是否进入当前图层 | 新图层含形变、基准网格不变 | 方案 A 失效 → 转 B |
| A | P0b：录制中导入是否清掉图层栈 | 先前图层保留 | 多图层录制不可行 → 转 B |
| B | P1：图层探测与计数（`Tool:Layers:3D Layer 0..7` + `Layers Scrollbar` + `SelectDown`） | 准确枚举层数与导航 | 导出侧无法枚举图层 |
| B | P2：强度路径 `Tool:Layers:Intensity` vs `Layer Intensity` | `[IExists]`+`[IGet]/[ISet]` 往返一致 | 强度无法还原 |
| C | P3：强度归零是否使网格回到基准（顺带产出 base/Layer 快照文件） | 归零后导出 = Base | 多图层污染无法规避 |

P4（可见性 eye IClick 坐标）**后置**：隔离功能，核心机制跑通后再单独验证；失败仅降级该项。

**P0 实测结论（2026-08-01，ZLayer_probe 一次运行，LayerA/1 + LayerB/0.5）**：

- ✅ 强度路径：`Tool:Layers:Intensity` 与 `Tool:Layers:Layer Intensity` 均存在；`[IExists]=1`、`[IsEnabled]=1`。
- ✅ `New` / `SelectDown` / `SelectUp` / `Rename` / `Layers Scrollbar` / `Import MDD` / `Record Deformation Animation` 均存在。
- ❌ `Tool:Layers:3D Layer 0..7` 不存在（槽位寻址不可用）。
- ❌ `Layers Scrollbar` `IGetMax=0` / `IGet=0`（无法借滚动条计数）。
- ❌ **标题导航法失效**：`[IGetTitle,Tool:Layers:Intensity]` 恒返回 `"Intensity"`，SelectDown/Up 不改变标题 → 依赖标题的计数法（连续相等/环绕）全部失效（环绕=1、连续=0 即死循环误判）。
- ❌ **P0a 失败**：全层归零后 `New` + 录制中 `Import` probe_Layer_0.goz → 新层 "Untitled Layer 1" 权重 1、**留驻录制态、无形变**。
- ✅ **P0b 通过**：录制导入未清掉图层栈（LayerA/B 保留未变）。
- ✅ **P3 通过**：全层强度归零导出 = 未变形基准网格（probe_Base.goz）；逐层强度 1 快照 probe_Layer_0/1.goz 导出成功。
- → **方案 A 不可行，转方案 B（MDD）为主路径**；图层导航改用**按名称寻址**（`Tool:Layers:<name>`，待 probe2 验证）。

**⚠️ 重大修正（2026-08-01，probe2 结果 + 用户额外信息）**：

probe2 暴露了**强度命令的真相**，推翻上述"方案 A 不可行"的结论：

1. **`[ISet/IGet,Tool:Layers:Intensity]` 是 UI 层假操作**（不触图层）。证据：probe1 Section C 用 `ISet(Intensity,0/1)` 归零/置 1 全部未生效 → 导出的 probe_Base/Layer_0/Layer_1.goz **三个文件完全相同（均 = 当前网格 LayerA@100%）**。
2. **`[ISet,Tool:Layers:<层名>,<值>]` 是真正的强度操作**。证据：probe2 Test1 的 `ISet(LayerA,0)`/`ISet(LayerB,0)` 把两层强度真归零（用户确认"最后 LayerA/B 强度都归 0"）。`IGet(图层路径)` 读强度待 probe4 确认。
3. **probe1 P0"无形变"真因**：导入的 probe_Layer_0.goz 本身 = 当前网格（导出时强度设置未生效）→ delta≈0 → 无形变。**录制导入机制未被证伪**。
4. **方案 A（录制导入）复活为唯一路径**，无需 DLL。用户手动验证：先归零（UI 真生效）→ New（录制）→ Tool>Import 有形变 .goz → 形变记录进新层；新建层导入不影响原有层。
5. Record Deformation Animation **弃用**（无 MDD 产出、无新层；probe2 的"归 0"实为 Test1 副作用，非其破坏）。

**方案 A 待 probe4 验证项**：① `IGet(图层路径)` 读强度；② 新层录制导入复现（用户手动流程脚本化）；③ 当前层身份读取（IGetTitle full path / IGetInfo / IGetStatus / 滚动条 IGetSecondary）；④ 退出录制 IClick REC 坐标。

**probe4 验证结果（2026-08-01）**：
- ① **确认**：`IGet(LayerA/LayerB)` 读强度有效（0-1 值域）；`IGet(Intensity)` UI 返回 100（顶部 Intensity 滑杆为 0-100 域，与按名称强度 0-1 域是两套体系，进一步证实 Intensity=UI 假操作）；`IGetTitle(LayerA,1)`=full path；`IGetInfo(LayerA)` 返回层内容描述（"LayerA SDiv 3 PolyPaint..."）；`IGetStatus(LayerA)`=1；强度往返 `ISet(LayerA,0.5)→IGet→ISet(LayerA,0)` 均正确。
- ② **部分确认**：`IPress Tool:Layers:New` + FileNameAsk 选 goz + `IPress Tool:Import` 能创建新层并记录形变（New 自动进入录制；IModGet 前后对比无法可靠检测录制态；出现两个同名 Untitled Layer 0 的异常需正式实现时用确定性命名规避）。
- ③ **部分确认**：`3D Layer 0/1` 槽位项 IExists=1 但 IGetTitle 为空；IGetTitle full path 可用。
- ④ **未确认**：IClick 盲试未验证退出录制（3D Layer 槽位 IGetTitle 空，无法作为坐标基准）。
- **IModGet 限制**：`IModGet(Tool:Layers:Intensity)` 报错 "Interface item does not have special modifiers"（滑杆无修饰位）；`IModGet(LayerA)` 可用（返回 0）。IModGet 仅适用于带 special modifiers 的项。

**⚠️ 缩放问题破案（2026-08-01，probe4aM 手动对照）**：
- 现象：脚本导出的 T4_A.goz 导入后形变整体等比缩小 ~70%（普通笔刷雕刻、无缩放操作、无 Dynamic、层权重=1 时）。
- 根因：`FileNameAsk` 返回**反斜杠**完整路径（`C:\...\T4_A.goz`）直接传给 `FileNameSetNext` → ZBrush 导出异常缩放。正式流程 ZBRunExport 一直用 `FileNameExtract` 提取目录 + **正斜杠**拼接（`dir/T4_A.goz`）再给 FileNameSetNext，从未踩坑。
- 修复：Probe4a 路径处理对齐 ZBRunExport。验证：Probe4a（脚本）与 Probe4aM（手动对话框）导出文件尺寸一致且与视口正常。
- **硬约束**：所有 `FileNameSetNext` 路径必须用正斜杠拼接（ZBridge 导出循环已满足；后续新增导出代码必须遵守）。

**✅ 导航/层数/强度/身份机制最终定案（2026-08-01，probe4f + probe4h）**：

- **导航**：`SelectUp`/`SelectDown` 每按 ±1 层，到栈底/栈顶 no-op（probe4f：栈底 LayerB 按 Down 无效、按一次 Up 即到 LayerA）。标题判等检测在**重名层**下不可靠 → 改用**计数法**：`SelectUp x(N+1)` 饱和必到顶。
- **层数**：`ISet(Tool:Layers:Layers Scrollbar,0,255)` → `IGetSecondary(Scrollbar)` = N（0-based）→ 总层数 N+1（probe4f 实测 N=1 = 2 层）。
- **滚动条 ISet 不选层**：`ISet(Scrollbar,0,i)` 不改变当前层（probe4f s0/s1 标题不变）→ 弃用。
- **`Layer Intensity` 滑杆 = 当前层强度**（probe4h，决定性）：`IGet(Tool:Layers:Layer Intensity)` 随当前层返回其强度（LayerA=1 / LayerB=0.5）；`ISet(...,v)` 写当前层强度（写 0.7 按名同读 0.7、LayerB 写 0.3 不影响 LayerA = 层间独立）。**全程选择式寻址，重名免疫** → 按名 `ISet(Tool:Layers:<名>,v)` 降级为仅探测用。
- **层名读取**：`IGetTitle(Tool:Layers:Layer Intensity)` = 当前层名；`IGetTitle(...,1)` = full path（probe4d2）。

**✅ 可见性/录制机制最终定案（2026-08-01，probe4g/4i/4j/4k）**：

- **可见性语义**：可见关**阻断形变**（probe4i 用户确认：LayerB 强度置 1 仍不可见时"网格没变化"）→ T3 快照必须先开目标层眼睛。
- **可见性读 = `IModGet` bit1（值 2）**（probe4g/4i 解耦矩阵：LayerA(1,开)=2 / LayerB(0.5,关)=0 / LayerA(0,自动关)=0）。`IGetStatus` 恒 1 无用；`IGetFlags` 恒 10（bit3=选中态等）无用。
- **可见性写 = `IClick(<层路径>, W-5, H/2)` 切换**（probe4k：IClick 右缘 Mod 0→2；层行 W=168 H=24，眼睛在最右缘）。`IModSet` 对图层**无效**（probe4j 双向写均不生效）→ 不可用。
- **强度=0 自动关眼**（用户确认"强度改为0后可见性自动关闭"；probe4k 置0 → Mod=0）；强度>0 **不会**自动开眼（probe4i）。
- **录制态读 = `IModGet` bit0（值 1）**；**写 = `IClick(<层路径>, W-25, H/2)` 切换**（probe4k 意外发现，w-25 命中 REC 区；**实现避开 w-25 以免误触录制**）。
- **可见性设置算法**：读 `IModGet` bit1 → 与期望不符 → `IClick(路径,W-5,H/2)` 一次（切换）→ 读回校验，失败重试/中止。W/H 每次 `IWidth`/`IHeight` 现读（调色板尺寸可变）。
- **行内坐标带（经验）**：W-5=眼睛（bit1）、W-25=REC（bit0）、中部=选中。仅用 W-5。

**✅ 隔离性审查（2026-08-01，用户要求"图层功能不影响其他功能"）**：

逐状态点核验 ZBRunLayerSnapshot 系列例程与导出主循环的交叉，确认互不干扰：

| 状态 | 快照前 | 快照内 | 快照后恢复 |
|------|--------|--------|-----------|
| SDiv | 主循环已恢复 `zbCurSdiv` | 切 `zbMaxSdiv`（顶点对齐） | 恢复 `zbCurSdiv` |
| Dynamic 预览 | `DynRestorePreview` 已恢复 | 按 `dynActive` 临时 `IUnPress` | 按 `dynActive` 重开 |
| 层强度 | BuildMem 写内存 | 归零→置1→置0 | RestoreMem 逐层恢复 |
| 层可见性 | `IModGet` bit1 写记录 | 开眼→置0自动关眼 | 先强度后可见性 |
| 当前层 | — | 停在栈顶 | 停在栈底（见"残留"） |
| 录制位 REC | 不动 | 全程不点 W-25 | 不变 |
| 子工具焦点 | `SubToolSelect,zbIdx` | 不切换 | 主循环尾恢复 `zbActiveST` |
| 内存 | — | 每子工具累积写入 | 尾 `MemDelete`；写盘仅当 `zbLayerOffset>0` |

交叉点结论：

- **与 0.5.0 重名检查**：重名即中止导出，图层例程根本不执行，无交互。
- **与 0.6.0 Dynamic**：`dynActive` 每子工具经 `ZBRunDynRead` 重读，快照用的即当前子工具值；临时关闭/恢复对称。
- **与 0.7.0 贴图**：`TexVerify` 在快照之前完成、精确匹配 `<stName>_TXTR.tif`；快照 goz（`_LayerBase`/`_Layer<i>`）产生的额外 `_TXTR.tif` 不参与任何检测逻辑，仅磁盘多余文件，不影响导入。
- **无图层子工具**：`IExists Scrollbar=0` → `zbLayerCount=0` → 整体跳过，零副作用、行为零变化。
- **索引一致性**：`Layer<i>.goz` 的 i == layers.txt 的 `layerIndex`（栈底=0），导入侧可按序重建。
- **内存推进模式**：RestoreMem 用 `+StrLength+1`，与 manifest 读取（`zbManOffset`）既有成功模式一致。
- **边界推演**：1 层、重名层、强度=0 自动关眼等场景自洽。

唯一已知残留（已评估可接受）：**图层选中焦点**——快照流程结束后当前选中层停在栈底，而非导出前用户选中的层。无持久语义、不影响任何功能（下一子工具从 ToTop 重新开始）；层可重名故无法可靠记录/恢复焦点位置。仅当用户导出后切回该子工具时图层面板选中项与导出前不同。

#### 4.8.6 方案 B 说明（P0 失败后的主路径）

- 导出侧：DLL（走 `FileExecute`，ZFileUtils 已验证的可靠同步路径；复用 `src/cpp/` 的 GoZ_Mesh 读写代码）读取 Base.goz + Layer_<i>.goz 的 POINT_LIST，生成标准 MDD 形变文件 `Layers/<name>/Layer_<i>.mdd`（frame0=Base 绝对坐标、frame1=Layer_i 绝对坐标），顺带校验 vertexCount。
- 导入侧：`[IPress,Tool:Layers:Import MDD]` 原生建层，无录制体操、无污染风险；其余（命名/强度/可见性/细分重跑）与方案 A 完全一致。
- 不推荐方案 C（design_next 原案 C++ 合并网格）：多图层录制基准污染问题依旧存在，且 DLL 成为必然依赖，复杂度高于 A、稳定性低于 B。

#### 4.8.7 版本与发布

- 版本号 **0.8.0**（头注释 `//Version: 0.8.0`、About 文案、IButton UI 版本 0.7→0.8）。
- 完成后同步 `releases/0.8.0/ZBridge/`（ZBridge.txt + ZBridgeData/，字节一致，UTF-8 BOM + CRLF）。
- `doc/ZBridge.md` / `doc/design_next.md` 功能三标记 ✅ 0.8.0；`development_log.md` 记录 0.8.0 章节。

---

## 五、功能四：颜色贴图还原（显式重绑） ✅ 已实现（0.7.0）

> 状态：0.7.0 已完成。实现为导出侧 `ZBRunTexDetect`（检测绑定 + 清除残留贴图文件）/`ZBRunTexVerify`（导出后确认自动生成的 `<子工具名>_TXTR.tif`）/`ZBRunTexExtAppend`（追加 `hasTexture`/`textureFile` 到 ext）+ 导入侧 `ZBRunTexRestore`（Phase 2 末尾显式重绑）。详见 `development_log.md` 0.7.0 章节。
> **实现取舍**：ZScript 无文件重命名/移动能力（ZFileUtils 仅重命名 UI 条目），且无目录列举命令，故贴图文件保留在导出根目录（与 goz 平级），`textureFile` 记录实际文件名（design_next §5.3 的兜底方案"记录自动生成的实际文件名，不强行改名"）。

### 5.1 机制背景

- GoZ 文件内**不嵌入图像数据**，只有 `GoZ_TAG_TEXTURE_MAP_PATH` 块（相对路径字符串）。
- 贴图本体是 ZBrush `Tool:Export` 时自动写到 .goz 旁边的独立 .tif，GoZ 工作流命名约定：颜色贴图 `_TXTR.tif`、法线 `_NM.tif`、置换 `_DM.tif`。
- 决定：**不依赖** ZBrush 导入时对该路径块的隐式解析，走显式重绑。

### 5.2 Manifest 扩展

贴图信息不新增 pipe 字段，写入 ext 扩展字段的两个键：

```text
hasTexture=1;textureFile=Textures/Body_TXTR.tif;
```

- `hasTexture`：0/1（导出时检查 Tool 是否绑定贴图，候选：`Tool:Texture Map:Texture On` 状态 + 贴图存在性判断）。
- `textureFile`：相对路径，如 `Textures/Body_TXTR.tif`。

### 5.3 Export 流程

1. `Tool:Export` 导出 goz 后，ZBrush 自动在同目录写出贴图 .tif。
2. 将该 .tif **重命名/移动**为确定名 `Textures/<子工具名>_TXTR.tif`（ZScript 文件重命名能力：候选 ZFileUtils 或 FileExecute；若不可行则记录自动生成的实际文件名，不强行改名）。
3. 写 manifest `hasTexture` / `textureFile`。

前置实测：确认 ZBrush 自动生成的贴图文件名规则（基于 goz 文件名还是 Tool 名、后缀形式）。

### 5.4 Import 流程（Phase 2 属性恢复阶段内）

对 `hasTexture=1` 的 SubTool：

1. `FileNameSetNext` 指向 `Textures/<名>_TXTR.tif`。
2. `[IPress,Tool:Texture Map:Import]`（预期自动绑定到当前 Tool 的 Texture 槽，需验证）。
3. `[ISet,Tool:Texture Map:Texture On,1]`。

### 5.5 处理要点

- **顺序**：放在名称恢复之后，并关注是否被后续操作重置（参照 Colorize 被重置的既有教训，必要时最后统一再设一次 Texture On）。
- 与 Polypaint 无冲突：顶点色走 GoZ 内嵌 MRGB 块，贴图走外部文件，两者独立。

### 5.6 验证点

1. 导出时自动生成的贴图文件名约定（决定是否需要重命名步骤）。
2. `Tool:Texture Map:Import` 是否自动绑定当前 Tool。
3. Texture On 状态往返、贴图克隆行为（是否克隆进 Texture 面板）。

---

## 六、Manifest 组织方式：9 字段 + ext 扩展

### 6.1 为什么不继续 pipe 追加字段

新功能共需 10+ 个新属性（动态细分 8 项 + 贴图 2 项）。若继续 pipe 追加，record 达 19 字段，需要 zbPipePos9–18 共 10 个新位置变量，解析代码臃肿、字段语义全靠位置记忆、极易错位。改用 **ext 扩展字段（key=value 组织）**。

### 6.2 格式

SubTool record = 0.4.0 的 9 个 pipe 字段 + 1 个 ext 字段：

```text
colorize|maxSdiv|curSdiv|subtoolEye|folderEye|isFolder|isOpened|folderName|name|ext\0
```

ext 内部格式：`key=value;` 串联，分号结尾：

```text
dynActive=1;dynFlat=0;dynSmooth=2;dynThick=0.5;dynSegs=2;dynPost=1;dynOffset=0.0;dynSmoothness=0.5;hasTexture=1;textureFile=Textures/Body_TXTR.tif;
```

完整示例：

```text
1|4|3|1|0|0|0||Body|dynActive=1;dynFlat=0;dynSmooth=2;dynThick=0.5;dynSegs=2;dynPost=1;dynOffset=0.0;dynSmoothness=0.5;hasTexture=1;textureFile=Textures/Body_TXTR.tif;\0
```

### 6.3 ext 键清单

| 键名 | 类型 | 来源功能 | 缺失时默认 |
|------|------|---------|-----------|
| `dynActive` | 0/1 | 动态细分 | 0 |
| `dynFlat` | int | 动态细分 | 0 |
| `dynSmooth` | int | 动态细分 | 0 |
| `dynThick` | float | 动态细分 | 0.0 |
| `dynSegs` | int | 动态细分 | 0 |
| `dynPost` | 0/1 | 动态细分 | 0 |
| `dynOffset` | float | 动态细分 | 0.0 |
| `dynSmoothness` | float | 动态细分 | 0.0 |
| `hasTexture` | 0/1 | 贴图 | 0 |
| `textureFile` | string | 贴图 | 空 |

### 6.4 解析设计

- 主解析 `ZBRunManParse` 只多解析 1 个 pipe 位置（pos9），现有 9 字段逻辑零改动。
- 新增 `ZBRunExtParse` 例程：输入 ext 字符串，对每个已知 key 执行 `StrFind,"key="` → `StrExtract` 到 `;`，再 `Val` 转数值。找不到该 key 即取默认值。
- 每个 SubTool 10 次 StrFind，SubTool 数量级下性能无虞。
- **向后兼容天然成立**：旧 manifest 无 ext 字段（pos9 找不到 `|`）→ ext 为空 → 全部默认；ext 中缺某 key → 该项默认。新增属性只需向清单加 key，格式不破坏。
- 可读性好：直接打开 manifest 即可看懂属性，调试不用数 pipe。

### 6.5 其他

- 图层元数据**不进**主 manifest，独立存 `Layers/layers.txt`（格式见 4.2）。
- 导出侧拼接 ext 用分步 `StrMerge`（沿用 0.4.0 避免超长 StrMerge 的既有做法）。

---

## 七、分阶段验证计划

| 阶段 | 内容 | 通过标准 |
|------|------|---------|
| P0 | 图层生死验证：单 SubTool 单 Layer，录制状态下导入形变 GoZ | 形变进入新 Layer，base mesh 不变 |
| P1 | 重名检查：构造同名 SubTool，导出中止并提示 | 重名被检出、导出中止、提示正确 ✅ 0.5.0 通过 |
| P2 | 动态细分 8 属性读写 + ext 拼接/解析往返 | 两个 ZBrush 版本读写往返一致，ext 解析取默认值正确 |
| P3 | 贴图显式重绑：单 SubTool 带贴图导出→导入 | Texture 槽绑定 + Texture On 恢复 ✅ 0.7.0 已实现（待实测验证） |
| P4 | 图层完整链路：单 SubTool 多 Layer（名称/顺序/强度/可见/启用） | 全部状态还原 |
| P5 | 图层 + 细分级别（最高级采样 → Reconstruct 后恢复图层） | 细分层级与图层共存正确 |
| P6 | 四功能合并：多 SubTool + Folder + 重名检查 + 动态细分 + 图层 + 贴图 | 全量往返 |

---

## 八、风险清单

| 风险 | 影响 | 对策 |
|------|------|------|
| 录制状态导入 GoZ 不进 Layer | 功能三整体失败 | P0 最先验证；失败走降级方案 |
| 图层面板 ZScript 路径不可用 | 功能三导出侧失败 | 先做单层 UI 路径探测脚本 |
| 贴图自动文件名不确定 | 功能四重命名步骤复杂化 | 实测确认；不行则记录实际文件名 |
| 低版本 ZBrush 缺动态细分属性 | 功能二部分属性不可还原 | `[IExists]` 判空跳过，不报错 |
| 顶点数/顺序不一致 | 图层 delta 套错 | vertexCount 校验，不一致跳过并报错 |
| ZScript 无文件重命名能力 | 贴图/图层文件整理受限 | ZFileUtils / FileExecute 备选；兜底记录实际文件名 |

---

## 九、已舍弃内容备忘（不要复活）

以下属于 0.4.0 之后的舍弃开发，后续不要再引入：

- `.zbridge` 单文件打包及 manifest.json 双轨制
- ZBridgePacker.exe 及 pack/unpack 请求-结果回写机制
- `SubTool_N.goz` 稳定编号命名（基线为子工具名命名 + 重名检查前置）
- `Meshes/` 子目录结构（0.4.0 为 goz 与 manifest 同级平铺）
