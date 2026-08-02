# ZScript 命令与 Python SDK 参考：动态细分 / 颜色贴图 / 雕刻图层

> **定位**：ZBridge 功能二（动态细分预览与属性还原）、功能四（颜色贴图还原）、功能三（雕刻图层还原）的固定参考文档。目标是为后续开发提供"全面、固定、稳定"的功能清单，避免逐文件测试的低效验证方式。
>
> **三功能边界（勿混淆）**：
> - **动态细分**（功能二）→ `Tool:Geometry:s.*`，8 项属性，走 manifest ext 字段。
> - **颜色贴图**（功能四）→ `Tool:Texture Map:*`，绑定的是**图像文件**（.tif），与 Polypaint 顶点色无关。
> - **雕刻图层**（功能三）→ `Tool:Layers:*`，承载的是**顶点形变数据**，与图片完全无关，走独立 `Layers/layers.txt`。
>
> **信息源**（按权威性排序）：
> 1. `D:\Maxon ZBrush 2025\ZData\ZLang\zcommands\commands.xml` —— ZBrush 安装包内权威 UI 命令定义（跨版本稳定，`trans` 为翻译表 ID）
> 2. help.maxon.net 官方用户手册：`dynamic-subdivision.html` / `settings.html` / `dynamic-thickness.html`
> 3. ZBrush Python SDK 2026.0.0 官方迁移手册（developers.maxon.net）：`man_zscript_migration.html` / `mod_zbr_cmds_gui.html` / `mod_zbr_cmds_modeling.html`
> 4. ZBridge v0.4.0 源码（`src/zscript/ZBridge.txt`）已实测可用的命令模式
> 5. ZBrushCentral 论坛实测确认（Dynamic 按钮路径）
>
> **配套文档**：`doc/design_next.md` 第三章（功能二规格）、第六章（ext 扩展格式）、第七章（P2 验证计划）。

---

## 一、动态细分 8 属性总览

全部 8 项属性位于 **Tool:Geometry 调色板的动态细分（Dynamic Subdivision）子区**，UI 路径统一以 `s.` 前缀标记（`s.` = Dynamic Subdivision 子调色板标记，与 `P.` Panel Loops、`B.` BevelPro、`D.` DynaMesh、`a.` ArrayMesh、`m.` NanoMesh 同级）。

| # | 属性 | 功能名（英文） | ext 键名 | 类型 | 说明 |
|---|------|---------------|---------|------|------|
| 1 | Dynamic 按钮 | Dynamic | `dynActive` | 0/1 | 动态细分预览总开关（按钮） |
| 2 | FlatSubdiv | Flat Subdivision | `dynFlat` | int | 平直细分模式级数（滑杆） |
| 3 | SmoothSubdiv | Smooth Subdivision | `dynSmooth` | int | 平滑细分模式级数，Catmull-Clark（滑杆） |
| 4 | Thickness | Thickness | `dynThick` | float | 厚度，0=关闭（单面）（滑杆） |
| 5 | Segments | Segments | `dynSegs` | int | 厚度循环段数（滑杆） |
| 6 | Post SubDiv | Post SubDiv | `dynPost` | 0/1 | 先细分后加厚度=硬边（按钮） |
| 7 | Offset | Offset | `dynOffset` | float | 偏移，正=向外/负=向内/0=两侧各半（滑杆） |
| 8 | Smoothness | Smoothness | `dynSmoothness` | float | 重叠拓扑平滑度（滑杆） |

### 1.1 权威 UI 路径（commands.xml 1762–1805 行）

```text
Tool:Geometry:SDiv               trans=2130   （细分级别，非动态专属）
Tool:Geometry:Reconstruct Subdiv trans=2164
Tool:Geometry:Divide             trans=2798
Tool:Geometry:Smt                trans=2799
Tool:Geometry:Suv                trans=2804
Tool:SubTool:DSDiv               trans=5179   （SubTool 级深度细分相关）
Tool:Geometry:s.Dynamic          trans=2806   ← 属性 1
Tool:Geometry:s.Apply            trans=2807   （动态→经典细分转换）
Tool:Geometry:s.QGrid            trans=2808   （QGrid 模式）
Tool:Geometry:s.Bevel            trans=2809   （QGrid 斜角）
Tool:Geometry:s.Chamfer          trans=2810   （QGrid 倒角）
Tool:Geometry:s.Coverage         trans=2811   （QGrid 覆盖率）
Tool:Geometry:s.Constant         trans=2812   （QGrid 常量）
Tool:Geometry:s.FlatSubdiv       trans=2813   ← 属性 2
Tool:Geometry:s.SmoothSubdiv     trans=2814   ← 属性 3
Tool:Geometry:s.Thickness        trans=7633   ← 属性 4
Tool:Geometry:s.Segments         trans=7634   ← 属性 5
Tool:Geometry:s.Post SubDiv      trans=7635   ← 属性 6
Tool:Geometry:s.Offset           trans=7636   ← 属性 7
Tool:Geometry:s.Smoothness       trans=7637   ← 属性 8
Tool:Geometry:s.MicroPoly        trans=7674   （MicroPoly 区域）
Tool:Geometry:s.MicroPoly On     trans=7675
Tool:Geometry:s.Fit              trans=7676
Tool:Geometry:s.Weld             trans=7677
Tool:Geometry:s.Scale            trans=7678
Tool:Geometry:s.Align            trans=7679
Tool:Geometry:s.Rot Z            trans=7680
Tool:Geometry:s.Rot X            trans=7681
Tool:Geometry:s.Prev             trans=7682
Tool:Geometry:s.Next             trans=7683
```

---

## 二、8 属性读写方法详表

通用规则：
- **按钮型控件**（Dynamic、Post SubDiv）：`[IGet]` 返回 **0/1**；设已知状态用 `[IPress]`（开）/`[IUnPress]`（关）；若需保持当前状态则先 `[IGet]` 再按需切换。
- **滑杆型控件**（FlatSubdiv/SmoothSubdiv/Thickness/Segments/Offset/Smoothness）：`[IGet]` 返回当前数值；`[ISet]` 写入数值。
- 所有路径读写前先 `[IExists]` 判空（低版本 ZBrush 无此属性则跳过，不报错——design_next.md §3.2 要求）。

| 属性 | 读（ZScript） | 写（ZScript） | Python SDK（`zbc`） | 有效值 | 备注 |
|------|--------------|--------------|---------------------|--------|------|
| Dynamic | `VarSet,dynActive,[IGet,Tool:Geometry:s.Dynamic]` | 开：`[IPress,Tool:Geometry:s.Dynamic]`；关：`[IUnPress,Tool:Geometry:s.Dynamic]` | `zbc.get("Tool:Geometry:s.Dynamic")` / `zbc.press(...)` / `zbc.un_press(...)` | 0/1 | 热键 D / Shift+D；导出 GoZ 前须临时关闭 |
| FlatSubdiv | `VarSet,dynFlat,[IGet,Tool:Geometry:s.FlatSubdiv]` | `[ISet,Tool:Geometry:s.FlatSubdiv,dynFlat]` | `zbc.get(...)` / `zbc.set(item, h_value)` | int ≥ 0，上限待实测 | QGrid/Flat/Smooth 三模式共用级数语义 |
| SmoothSubdiv | `VarSet,dynSmooth,[IGet,Tool:Geometry:s.SmoothSubdiv]` | `[ISet,Tool:Geometry:s.SmoothSubdiv,dynSmooth]` | `zbc.get(...)` / `zbc.set(...)` | int ≥ 0，上限待实测 | Catmull-Clark |
| Thickness | `VarSet,dynThick,[IGet,Tool:Geometry:s.Thickness]` | `[ISet,Tool:Geometry:s.Thickness,dynThick]` | `zbc.get(...)` / `zbc.set(...)` | float；0=关闭（单面），范围待实测 | 与 2021.5 Thick Skin 功能同源 |
| Segments | `VarSet,dynSegs,[IGet,Tool:Geometry:s.Segments]` | `[ISet,Tool:Geometry:s.Segments,dynSegs]` | `zbc.get(...)` / `zbc.set(...)` | int ≥ 0，范围待实测 | 厚度循环段数 |
| Post SubDiv | `VarSet,dynPost,[IGet,Tool:Geometry:s.Post SubDiv]` | `[IPress,Tool:Geometry:s.Post SubDiv]` / `[IUnPress,...]` | `zbc.get(...)` / `zbc.press(...)` / `zbc.un_press(...)` | 0/1 | 先细分后厚度=硬边 |
| Offset | `VarSet,dynOffset,[IGet,Tool:Geometry:s.Offset]` | `[ISet,Tool:Geometry:s.Offset,dynOffset]` | `zbc.get(...)` / `zbc.set(...)` | float；正=外向/负=内向/0=各半，范围待实测 | |
| Smoothness | `VarSet,dynSmoothness,[IGet,Tool:Geometry:s.Smoothness]` | `[ISet,Tool:Geometry:s.Smoothness,dynSmoothness]` | `zbc.get(...)` / `zbc.set(...)` | float，范围待实测 | 重叠拓扑平滑 |

> `varSet` 中的变量命名沿用 ZBridge 硬约束：**camelCase、无下划线**（`dynActive`、`dynFlat` 等）。
> float 值以字符串原样存取（`Val`/`StrMerge` 转换），不额外定精度（design_next.md §3.2）。

### 2.1 状态变量与 ext 键（manifest 存储）

功能二的 8 项属性在 manifest **ext 扩展字段**（`key=value;` 串联）中以固定键名存取，缺失时取默认值：

| ext 键 | 类型 | 缺失默认 |
|--------|------|---------|
| `dynActive` | 0/1 | 0 |
| `dynFlat` | int | 0 |
| `dynSmooth` | int | 0 |
| `dynThick` | float | 0.0 |
| `dynSegs` | int | 0 |
| `dynPost` | 0/1 | 0 |
| `dynOffset` | float | 0.0 |
| `dynSmoothness` | float | 0.0 |

（另有功能四贴图键 `hasTexture` / `textureFile`，见 design_next.md §6.3。）

解析规则（design_next.md §6.4）：`ZBRunExtParse` 对每个已知 key 执行 `StrFind,"key="` → `StrExtract` 到 `;` → `Val` 转数值；找不到即取默认。向后兼容天然成立。

---

## 三、ZScript 通用命令 ↔ Python SDK 映射

来源：官方 ZScript Migration Manual（Python SDK 2026.0.0）。Python 侧统一入口：`from zbrush import commands as zbc`（Python 3.11.9，启动参数 `-script`，批处理 `-batch`）。

### 3.1 界面命令（GUI 项）

| ZScript 命令 | Python SDK 接口 | 说明 |
|-------------|----------------|------|
| `[IGet,<itemPath>]` | `zbc.get(item_path)` | 读按钮 0/1、滑杆数值 |
| `[ISet,<itemPath>,<value>]` | `zbc.set(item_path, h_value)` | 写滑杆/按钮值 |
| `[IPress,<itemPath>]` | `zbc.press(item_path)` | 按下按钮（开关类：触发/置开） |
| `[IUnPress,<itemPath>]` | `zbc.un_press(item_path)` | 抬起按钮（置关） |
| `[IToggle,<itemPath>]` | `zbc.toggle(item_path)` | 切换按钮状态 |
| `[IExists,<itemPath>]` | `zbc.exists(item_path)` | 判空（版本兼容检查） |
| `[IGetMax,<itemPath>]` | `zbc.get_max(item_path)` | 滑杆最大值（实测范围用） |
| `[IGetMin,<itemPath>]` | `zbc.get_min(item_path)` | 滑杆最小值（实测范围用） |
| `[IGetTitle,<itemPath>]` | `zbc.get_title(item_path)` | 读标题（ZBridge 用于取子工具名/当前层名） |
| `[IsEnabled,<itemPath>]` | `zbc.is_enabled(item_path)` | 项是否可用（细分级别判断前置） |
| `[IGetInfo,<itemPath>]` | `zbc.get_info(item_path)` | 读项目信息字符串（图层内容描述） |
| `[IGetFlags,<itemPath>]` | `zbc.get_flags(item_path)` | 读选择状态等标志（SubTool 选中态） |
| `[IModGet,<itemPath>]` | `zbc.get_mod(item_path)` | 读修饰位（图层录制位 bit1；SubTool Add/Sub/…/可见性位） |
| `[IModSet,<itemPath>,<value>]` | `zbc.set_mod(item_path, value)` | 写修饰位 |
| `[IClick,<itemPath>,<x>,<y>]` | `zbc.click(item_path, x, y)` | 模拟点击项目内坐标（图层 REC 图标开关） |
| `[IWidth,<itemPath>]` | `zbc.get_width(item_path)` | 读项目宽度（计算 REC 图标点击位置） |
| `[IHeight,<itemPath>]` | `zbc.get_height(item_path)` | 读项目高度 |
| `[IGetSecondary,<itemPath>]` | `zbc.get_secondary(item_path)` | 读次级值 |
| `[IGetStatus,<itemPath>]` | `zbc.get_status(item_path)` | 读状态字符串/值 |
| `[ISetStatus,<itemPath>,<value>]` | `zbc.set_status(item_path, value)` | 写状态 |
| `[SubToolGetStatus,<index>]` | `zbc.get_subtool_status(index)` | 读 SubTool 状态位 |
| `[SubToolSetStatus,<index>,<value>]` | `zbc.set_subtool_status(index, value)` | 写 SubTool 状态位 |
| `[SubToolGetActiveIndex]` | `zbc.get_active_subtool_index()` | 当前激活 SubTool 索引 |
| `[FileNameSetNext,<path>]` | `zbc.set_next_filename(path)` | 预设下一个加载/保存的文件名（贴图导入用） |

### 3.2 脚本级命令（无 Python 等价物）

以下为 ZScript 脚本语法级命令，Python 端不需要对应（Python 直接写语言级逻辑）：

```text
[VarSet] [If]/[Else]/[Endif] [Loop]/[Next] [Return] [Load]/[Save]
[Note]/[Ok]/[Message] [FileNameSetNext] [IPress]（作用于文件导入按钮时）
```

---

## 四、ZScript 状态管理与兼容性硬约束

以下约束来自 ZBridge v0.4.0 实测经验（`development_log.md` / `design_next.md` 基线说明），**功能二实现必须遵守**：

1. **位运算不可靠**：`|`、`&` 在 `[VarSet]` 赋值中不可靠，必须用 `If` 判断 + 加减算术替代。
   例如：`If,(zbStatus & 1) == 0, VarSet,zbStatus,zbStatus + 1`。
2. **判空保护**：所有 UI 路径读写前先 `[IExists,<path>]`，返回 0 则跳过该项（低版本兼容）。
3. **编码**：ZScript 文件用 **UTF-8 BOM + CRLF**。
4. **变量命名**：camelCase、无下划线（ZBrush 解析器硬限制）。
5. **导出前临时关闭 Dynamic 预览**：避免动态细分效果烘焙进 GoZ 几何；导出后恢复原值（design_next.md §3.2）。
6. **导入恢复顺序**：动态细分属性恢复放在 Subdivision 恢复（Reconstruct Subdiv）**之后**，避免被重建细分重置（design_next.md §3.2）。
7. **StrMerge 分步拼接**：避免超长 StrMerge，ext 字符串分步拼接（0.4.0 既有模式）。
8. **细分级别读写**：`[IGet,Tool:Geometry:SDiv]` / `[IGetMax,Tool:Geometry:SDiv]`，读前先 `[IExists]` + `[IsEnabled]` 判断；GoZ 导出在最高细分级别进行，导出后恢复原级别。

---

## 五、GoZ 格式与动态细分

### 5.1 GoZ_SubDiv 结构体（`refrenece/goz_sdk/Sources/GoZ_Binary.h`）

```c
struct GoZ_SubDiv {
    unsigned int subdivLevles;           // how many subdivisions this mesh has
    unsigned int currentSubdivLevel;     // current subdiv level; 0=1st level
    unsigned int dynamicSharpSubdiv;     // how many dynamic sharp subdivisions
    unsigned int dynamicSmoothSubdiv;    // how many dynamic smooth subdivisions
};
```

### 5.2 关键结论

- GoZ 文件**仅保存动态细分的级数计数**（sharp/smooth），**不保存完整 8 属性集**（Dynamic 开关、Thickness、Segments、Post SubDiv、Offset、Smoothness 均不落盘）。
- 因此功能二必须走 **manifest ext 扩展字段** 承载完整属性（见 §2.1），GoZ 只负责几何本体。
- 动态细分设置保存在 **ZPR/ZTL 工程文件** 中（官方 workflow.html），与 ZBridge 的导出/导入流程无关。

---

## 六、颜色贴图（Texture Map）属性与状态

> **边界**：本功能绑定的是**外部图像文件**（GoZ 导出时自动生成的 `.tif`），用于 Tool 的 Texture 槽，与 Polypaint 顶点色（GoZ 内嵌 MRGB 块）独立（design_next.md §5.5）。
> 参考：design_next.md 第五章（功能四）。

### 7.1 属性/命令总览（commands.xml 2336–2353 行）

| 命令 | UI 路径 | trans | 类型 | 说明 |
|------|--------|------|------|------|
| 纹理缩略图/当前绑定 | `Tool:Texture Map:TextureMap` | 2540 | 项目 | `[IGetTitle]` 读绑定纹理名，空则未绑定（`hasTexture` 判定） |
| Texture On | `Tool:Texture Map:Texture On` | 2541 | 0/1 | 贴图显示开关（导入后须置 1） |
| Clone Txtr | `Tool:Texture Map:Clone Txtr` | 2542 | 按钮 | **克隆当前纹理到 Texture 面板**（官方文档：Duplicates the current texture and adds it to the Texture palette；方向 tool→palette，不能用于绑定） |
| New Txtr | `Tool:Texture Map:New Txtr` | 2543 | 按钮 | 新建空白纹理 |
| Fix Seam | `Tool:Texture Map:Fix Seam` | 2586 | 按钮 | |
| Transparent | `Tool:Texture Map:Transparent` | 2544 | 0/1 | 透明背景 |
| Antialiased | `Tool:Texture Map:Antialiased` | 2545 | 0/1 | 抗锯齿 |
| Fill Mat / FillColor / FillGrad | `Tool:Texture Map:Fill*` | 2546-2548 | 按钮 | 填充 |
| New From Polypaint | `Tool:Texture Map:New From Polypaint` | 2553 | 按钮 | 顶点色→纹理 |
| New From Masking | `Tool:Texture Map:New From Masking` | 2555 | 按钮 | 遮罩→纹理 |
| New From UV Map / UV Check / Vertex Order / Poly Order | `Tool:Texture Map:New From *` | 2558-2561 | 按钮 | 生成纹理 |

### 7.2 功能四读写方法（design_next.md §5.4）

| 步骤 | ZScript | Python SDK |
|------|---------|-----------|
| 判定是否绑定贴图 | `[IGetTitle,Tool:Texture Map:TextureMap]` 非空 → `hasTexture=1` | `zbc.get_title(...)` |
| 预设导入文件名 | `[FileNameSetNext,Textures/<名>_TXTR.tif]` | `zbc.set_next_filename(...)` |
| 记录导入前面板纹理数 | `[VarSet,zbTexCount,[IGetMax,Texture:Item Info]]` | - |
| 导入（异步） | 优先 `[FileNameSetNext]` + `[IPress,File:Texture:Import]`（实测按钮提示路径，`[IExists]` 判空）；兜底 `Texture:Import`（老版本） | `zbc.set_next_filename(...)` + `zbc.press(...)` |
| 等待导入完成 | `[Loop,3000,[If,[IGetMax,Texture:Item Info] > zbTexCount,[LoopExit]] [Delay,0.1]]` | - |
| 读取纹理标题 | `[ISet,Texture:Item Info,[IGetMax,Texture:Item Info]]` 选中刚导入纹理（**关键前置**：ZB 怪癖，`Current Texture` 标题需 ISet 选中后才刷新，否则读为空 → 绑定块整体跳过）；标题读 `Texture:Current Texture`（兜底 `Texture:Item Info` + 去尾 2 字符） | - |
| 翻转垂直（ZB 通病） | `[IPress,Texture:Flpv]`（**Texture 面板**，录制实证；兜底 `Texture:FlipV`/`Texture:Flip Vertically`，`[IExists]` 判空） | `zbc.press(...)` |
| 绑定到子工具 | `[SubToolSelect,zbIdx]`（0.7.6：显式重选目标子工具）→ `[IPress,[StrMerge,"Texture:",[Var,zbTexTitle]]]` → `[IPress,Tool:Texture Map:TextureMap]` → `[If,[IExists,PopUp:<名>],[IClick,PopUp:<名>]]`（0.7.6：官方规范拾取器提交用 IClick）+ `[If,[IExists,PopUp:<名>],[IPress,PopUp:<名>]]` 兜底（0.7.7：IClick 提交后拾取器已关，IExists=0 自动跳过，避免误报错）；`[IGetTitle,Tool:Texture Map:TextureMap]` 验证，`[Loop,3]` 重试 | `zbc.press(...)` |
| 完成后面板置空 | ✅ 已验证（0.7.10）：`[If,zbTexImported == 1,[If,[IExists,Texture:Remove],[IPress,Texture:Remove]]]`（Phase 2 结束后清面板当前纹理，**不影响 Tool 槽已绑定贴图**）。绑定依赖面板纹理存在 + `ISet` 选中读取标题，故清理放在全部绑定完成后 | `zbc.press(...)` |
| 打开贴图显示 | `[ISet,Tool:Texture Map:Texture On,1]` | `zbc.set("Tool:Texture Map:Texture On", 1)` |

- ext 键：`hasTexture`（0/1）/ `textureFile`（相对路径 `Textures/<名>_TXTR.tif`），缺失默认 0 / 空。
- **顺序约束**：放在名称恢复之后；关注是否被后续操作重置，必要时最后统一再设一次 Texture On（design_next.md §5.5，参照 Colorize 教训）。
- **导入后克隆行为**（是否克隆进 Texture 面板）需实测（design_next.md §5.6 验证点 3）。

### 7.3 GoZ 贴图命名约定（design_next.md §5.1）

- GoZ 文件内**不嵌入图像数据**，仅 `GoZ_TAG_TEXTURE_MAP_PATH` 块存**相对路径字符串**。
- `Tool:Export` 导出 goz 时自动在同目录写出贴图 `.tif`，命名约定：颜色 `_TXTR.tif`、法线 `_NM.tif`、置换 `_DM.tif`。
- 导出侧实测项：自动生成文件名规则（基于 goz 文件名还是 Tool 名）→ 决定是否需要重命名为确定名 `Textures/<子工具名>_TXTR.tif`（design_next.md §5.3）。

---

## 七、雕刻图层（3D Layers）属性与状态

> **边界**：图层承载**顶点形变数据**，与贴图/图片无关（design_next.md §4）。参考：design_next.md 第四章（功能三）。
> **关键结论（官方 ZScript 无专用图层命令）**：marcus_civis 明确"没有特定的 3D Layers zscript 命令"。图层操作全部走**通用 UI 命令 + 界面体操**（`IModGet`/`IClick`/`IWidth` 模拟点击 REC 图标、按名称 `ISet` 选择层）。
> ⚠️ **8.5 为 probe 实测定案（2026-08-01，权威，以它为准）**：8.2-8.4 为早期官方资料推论，与 8.5 冲突处一律以 8.5 为准。

### 8.1 命令总览（commands.xml 2046–2071 行）

| 命令 | UI 路径 | trans | 类型 | 说明 |
|------|--------|------|------|------|
| 层列表滚动条 | `Tool:Layers:Layers Scrollbar` | 2363 | 滑杆(双值) | `[ISet,path,min,max]`，控制 8 层一组可见窗口 |
| 层槽位按钮 ×8 | `Tool:Layers:3D Layer 0..7` | 2364-2371 | 按钮 | 当前可见窗口的 8 个槽位 |
| 强度 | `Tool:Layers:Intensity` | 2372 | 滑杆 | 当前层强度；**旧版脚本用 `Tool:Layers:Layer Intensity`（2011-2015 时代），两路径均需实测** |
| 选择上/下 | `Tool:Layers:SelectUp` / `SelectDown` | 2373/2374 | 按钮 | 逐层移动当前选择（无名层时唯一可靠方式） |
| 移动上/下 | `Tool:Layers:MoveUp` / `MoveDown` | 2375/2376 | 按钮 | 改变层顺序 |
| 新建 | `Tool:Layers:New` | 2377 | 按钮 | 创建新层（进入录制） |
| 重命名 | `Tool:Layers:Rename` | 2378 | 按钮 | 打开命名对话框；备选 ZFileUtils `RenameCurrentLayer` |
| 复制 | `Tool:Layers:Duplicate` | 2379 | 按钮 | |
| 删除 | `Tool:Layers:Delete` | 2387 | 按钮 | |
| 拆分 | `Tool:Layers:Split` | 2380 | 按钮 | |
| 向下合并 | `Tool:Layers:Merge Down` | 2381 | 按钮 | |
| 反转 | `Tool:Layers:Invert` | 2383 | 按钮 | |
| Bake All | `Tool:Layers:Bake All` | 2384 | 按钮 | 烘焙全部层（降级方案用） |
| 导入 MDD | `Tool:Layers:Import MDD` | 2385 | 按钮 | |
| MDD 速度 | `Tool:Layers:MDD Speed` | 2386 | 滑杆 | |
| 录制形变动画 | `Tool:Layers:Record Deformation Animation` | 7673 | 按钮 | |

### 8.2 关键 ZScript 模式（ZBrushCentral 实测，marcus_civis）

**当前选中层 full path**（probe4d2/4h 实测；重名免疫，勿用按名拼接）：

```text
[VarSet,layerPath,[IGetTitle,"Tool:Layers:Layer Intensity",1]]   ; full path，供 IModGet/IClick/IWidth/IHeight
```

**录制状态读取**（`IModGet` **bit0** = 录制中，probe4k 实测）：

```text
[If,([IModGet,layerPath] & 1) == 1, ...]   ; 录制中
```

**录制开关（模拟点击 REC 图标，probe4k 实测坐标）**：

```text
[VarSet,wid,[IWidth,layerPath]]
[IClick,layerPath,wid-25,[IHeight,layerPath]/2]   ; W-25 处为 REC；⚠️ 实现避开此坐标防误触录制
```

**图层内容信息**（`IGetInfo`，含 "PolyPaint (Empty)" 等描述）：

```text
[VarSet,layerInfo,[IGetInfo,layerPath]]
```

**层选择与导航**（⚠️ probe4f/4h 实测：滚动条 `ISet` 不选层、按名 `ISet` 仅探测用——重名层不可靠）：

```text
[IPress,Tool:Layers:SelectUp]              ; 逐层上移；计数法 SelectUp x(总层数) 饱和到顶（见 8.5）
[IPress,Tool:Layers:SelectDown]            ; 逐层下移（到栈底 no-op）
```

### 8.3 功能三流程映射（design_next.md §4.3/§4.4）

> ⚠️ 本表强度命令均已由 probe4h 实测修正：一律用 `Tool:Layers:Layer Intensity`（选择式）；可见性/录制用 `IClick` 坐标已定案（见 8.5）。

| 流程点 | ZScript 命令 | 状态管理 |
|--------|-------------|---------|
| 创建新层 | `[IPress,Tool:Layers:New]` | 创建后自动进入录制 |
| 采样导出（每层快照） | 层选择（SelectDown 逐层）/ 强度临时置 1.0（`[ISet,Tool:Layers:Intensity,1]`） | 导出 `Layer_<i>.goz` 前记录原始强度/可见/启用 |
| 关闭全部层影响 | 逐层 `[ISet,Tool:Layers:Intensity,0]` | 导出 `Base.goz` |
| 录制中导入形变 GoZ | New → 录制中 → `FileNameSetNext` + `Tool:Import` | 退出录制（`[ISet,Tool:Layers:Intensity,0]` 或 IClick REC） |
| 强度/可见/启用恢复 | 强度=`[ISet,Tool:Layers:Intensity,<原值>]`；可见/启用**无直接命令** | layers.txt 记录；不可控项走降级 |

### 8.4 状态约束与风险

1. **✅ 可见性已实测闭环（probe4g/4i/4k）**：读=`IModGet` bit1（值2），写=`IClick(路径,W-5,H/2)` 切换；强度=0 自动关眼、强度>0 不会自动开眼。**启用态无 ZScript 读取途径 → 记录但不还原**（用户确认）。
2. **同名层陷阱**：按名称选择/读取信息时命中的是**第一个**同名层（marcus_civis 警告）→ ZBridge 全程**选择式寻址**（滑杆 + 计数法导航），重名免疫（probe4h 定案）。
3. **IModGet 前提**：仅适用于带 special modifiers 的项（图层行可用；滑杆报 "does not have special modifiers"）；需 full path 参数。
4. **✅ 强度路径已实测（probe4d1/4h）**：`Tool:Layers:Layer Intensity`=真实强度（0-1 域，选择式）；`Tool:Layers:Intensity`=UI 假操作（0-100 域）弃用。
5. **顶点数一致性校验**：导入侧用 `vertexCount` 校验，不一致跳过该层并报告（design_next.md §4.5）。
6. 导出侧"仅激活单层"采样、`layers.txt` 记录格式见 design_next.md §4.2。

### 8.5 实测定案速查（ZLayer_probe1/2/4 全系列，2026-08-01，**权威，编码直接调用**）

> 只给结论，省略推演过程。probe1/2 破假象、probe4a-4k 定机制。T3 导出侧已按本节省实现（ZBRunLayerSnapshot 系列例程）。

**机制速查表**：

| # | 机制 | 定案结论 |
|---|------|---------|
| 1 | **层数** | `[ISet,Tool:Layers:Layers Scrollbar,0,255]` → `[IGetSecondary,Scrollbar]` = N（0-based）→ 总层数 **N+1**；⚠️ 无图层判定：先 `IExists(Layer Intensity)` + `IsEnabled(Layer Intensity)`（无层时滑杆禁用）才碰 Scrollbar——空列表上 ISet/IGetSecondary 未定义（T3 实测闪退） |
| 2 | **导航** | `SelectUp`/`SelectDown` 每按 ±1 层，到栈底/栈顶 **no-op**；计数法 `SelectUp x(N+1)` 饱和必到顶（重名免疫，**勿用标题判等**） |
| 3 | **当前层强度** | `[IGet/ISet,Tool:Layers:Layer Intensity,<值>]` = 当前层强度（0-1 域，选择式寻址、层间独立、重名免疫） |
| 4 | **层名 / full path** | `[IGetTitle,Tool:Layers:Layer Intensity]` = 当前层名；`[IGetTitle,...,1]` = full path（供 IModGet/IClick/IWidth/IHeight） |
| 5 | **可见性读** | `[IModGet,<full path>]` **bit1（值2）** = 可见；实测：LayerA(强度1,开)=2 / LayerB(0.5,关)=0 / 强度0自动关=0；`IGetStatus` 恒1、`IGetFlags` 恒10 均无用 |
| 6 | **可见性写** | `[IClick,<路径>,W-5,H/2]` 切换一次；W/H 用 `[IWidth]/[IHeight]` **现读**（层行实测 W=168 H=24，眼睛在最右缘）；`IModSet` 对图层**无效** |
| 7 | **强度↔可见联动** | 强度=0 **自动关眼**（ZBrush 强制）；强度>0 **不会**自动开眼 → 快照必须先开眼再置 1 |
| 8 | **录制位** | `IModGet` **bit0（值1）** = 录制中；写 = `IClick(路径,W-25,H/2)` 切换；⚠️ **实现避开 W-25 防误触录制** |
| 9 | **假操作（弃用）** | `[ISet/IGet,Tool:Layers:Intensity]` 是 UI 假操作（不触图层，0-100 域）；按名 `[ISet,Tool:Layers:<名>,v]` 仅探测用（重名层不可靠） |
| 10 | **无效/不可用** | `3D Layer 0..7` 槽位路径不存在；滚动条 `ISet` 不选层；`IModGet` 对滑杆报 "does not have special modifiers" |

**硬约束**：`FileNameSetNext` 路径必须**正斜杠**拼接（`FileNameExtract` 取目录 + `/`）；反斜杠 → GoZ 导出缩放 ~70%（probe4aM 破案）。`StrExtract` 第三参数 = **终点索引（含）**（与 ZBRunManParse 已验证模式 `StrExtract(s,pipeK+1,pipeK+1-1)` 一致）；误传长度公式 → 终点<起点 → 负长度 → 堆损坏延迟闪退（T3 根因）。

**layers.txt 记录格式**（0.8.0 定稿，null-terminated records）：

```text
subtoolName|layerIndex|layerName|intensity|visible|enabled|vertexCount\0
```

- **layerIndex 0 = 原始栈底层**：ZBrush 新层总是插入栈顶 → 导入须按 layerIndex 0→N 顺序 `New`，重建后栈序一致。
- `enabled`/`vertexCount` 无 ZScript 读取途径，暂记 `0` 占位（用户确认：启用态记录但不还原）。

**导出快照文件**（方案 B 平级命名）：`<stName>.goz`（当前态）+ `<stName>_LayerBase.goz`（全层归零基准，导入侧主网格）+ `<stName>_Layer<i>.goz`（逐层快照，i=layerIndex）。

**快照流程**（T3 已实现）：归零全部 → 导出 Base → 逐层（**开眼 → 置 1 → 导出 Layer<i> → 置 0**）→ 恢复各层原强度+原可见性；期间**保持最高 SDiv + 临时关 Dynamic 预览**（否则快照几何与主网格不对齐）。

**恢复算法**（T4 导入侧用）：先恢复强度（强度=0 自动关眼、>0 不开眼）→ 仅"期望开且当前关"时 `IClick(W-5)` 一次；期望关恒无需操作。

**导入流程**（T4 已实现，ZBRunLayerImpLoad/ImpMatch/ImpRec/RestoreImport 四例程；**顺序定案不可调换**）：①加载 layers.txt（`MemCreateFromFile`，不存在则 `zbLayerImpOk=0` 全程零行为变化）；②Phase 1：有层子工具改导 `<stName>_LayerBase.goz` 作主网格（缺失回退主 goz）；③Phase 2 细分还原（现有 Reconstruct 块，**先行**）→ `IGetMax(SDiv)` 切最高（快照均在最高 SDiv 导出，顶点一一对齐）→ 按 layerIndex **升序**建层（k>0 先全部归零使网格=Base → `New`（自动录制）→ `FileNameSetNext` 正斜杠 + `Tool:Import` → `IModGet bit0=1` 确认后 `IClick(W-25)` 退录制 → ZFU 命名，失败降级跳过）→ 最终 pass 恢复各层强度+可见性（双向：不一致才点 W-5）→ 切回 `zbCurSdiv`。录制导入只动顶点不动基网格，细分历史保留，**无需重跑 Reconstruct**。形变闭环：导出 B=归零基准、Layer_i=B+d_i → 导入 delta=d_i → 最终 B+Σd_i×int_i = 原当前态。

**方案演进**：probe1 P0"录制导入无形变"是假象（强度命令假操作 → delta≈0）→ probe2 证明录制导入可行 → **方案 A（录制导入）为唯一路径**；`Record Deformation Animation` 弃用（无 MDD 产出、无新层）。

**隔离性保障**（2026-08-01 审查结论，T3 已按此实现）：快照期间 SDiv 切最高后恢复 `zbCurSdiv`、Dynamic 按 `dynActive` 临时关后恢复、层强度/可见性经 `zbLayerMem` 记录后逐层恢复；全程**不点 W-25**（录制位不动）、不切换子工具、不触碰子工具可见性；无图层子工具（`IsEnabled(Layer Intensity)=0` 防护）整体跳过零副作用；`layers.txt` 仅当 `zbLayerOffset>0` 写出且内存块恒 `MemDelete`。唯一残留：图层选中焦点停在栈底（可接受，不影响功能）。

---

## 八、待实测验证项汇总（design_next.md P0–P4）

| 项 | 验证方法 | 目标 |
|----|---------|------|
| 8 属性 UI 路径在两个 ZBrush 版本可用 | 探测脚本：`[IExists]` + `[IGet]/[ISet]` | 全部路径返回存在且读写往返一致 |
| 滑杆数值范围 | `[IGetMin]/[IGetMax]`（FlatSubdiv/SmoothSubdiv/Thickness/Segments/Offset/Smoothness） | 确认每项 min/max，补全 §2 的"待实测" |
| Dynamic 按钮读法 | `[IGet]` 返回 0/1，`[IPress]/[IUnPress]` 切换 | 确认按钮语义 |
| 关闭预览导出 GoZ 后几何形态 | 导出后比较 | 确认为动态细分未应用形态 |
| ext 拼接/解析往返 | 往返导出→导入 | 8 属性一致；缺失 key 取默认值正确 |
| `File:Texture:Import` 主路径（按钮提示实测） | `[IExists]` 判空 + `[IPress]` | 0.7.3 修订：确认实际路径为 `File:Texture:Import`；`Tool:Texture Map:Import` 实测弹错已移除。0.7.4：脚本模式**不自动绑定** Tool 槽，须显式拾取器绑定 |
| `Texture:Flpv`（Texture 面板 Flip V，录制实证） | `[IExists]` 判空 + `[IPress]` | 0.7.4 修订：翻转修复 ZB 垂直翻转通病；`Tool:Texture Map:Flip Vertically` 路径不存在已移除（待实测命中） |
| `Texture:Item Info` / `Texture:Current Texture` | `[IGetMax]/[ISet]/[IGetTitle]` | 0.7.4：选中刚导入纹理 + 读取标题用于 `PopUp:` 绑定（待实测标题格式） |
| 面板条目按下 `Texture:<名>`（录制实证） | `[IPress,[StrMerge,"Texture:",[Var,zbTexTitle]]]` | 0.7.5：模拟手动选择触发自动贴到子工具（录制脚本 `[IPress,Texture:example]`）；补 PopUp 点击 |
| 拾取器 PopUp 绑定 + 首次失效怪癖 | `[IPress,Tool:Texture Map:TextureMap]` + `[If,[IExists,PopUp:<名>],[IClick,PopUp:<名>]]` + `[If,[IExists,PopUp:<名>],[IPress,PopUp:<名>]]` 兜底，`[SubToolSelect,zbIdx]` 前置 + `[Loop,3]` 验证重试 | 0.7.4：绑定到子工具；确认 PopUp 名称与面板纹理标题一致。0.7.5：PopUp 单独仅设面板活动纹理，须配合 `Texture:<名>` 按下。0.7.6：PopUp 提交改用 IClick（2015 官方规范，工具贴图槽提交用 IClick）；绑定前显式重选子工具（Tool 贴图槽每子工具一份）。0.7.7：IClick 提交后拾取器关闭，IPress 兜底须 IExists 判空，否则报 "Interface item could not be found" |
| 贴图自动文件名规则 | 带贴图 Tool 导出 goz 后观察同目录文件 | 确认 `_TXTR.tif` 命名基准，决定重命名步骤 |
| Texture On 往返 + 克隆行为 | 导出→导入 | 槽绑定 + 显示恢复；克隆行为确认 |
| **ISet 为绑定前置**（0.7.9 发现，0.7.10 验证） | ✅ 已验证：移除 ISet → 绑定全部静默失败；恢复 ISet → 绑定正常 | ZB 怪癖：`Current Texture` 标题需 `ISet` 选中后才刷新；无 ISet → `zbTexTitle` 空 → 绑定块 `[If,zbTexTitle>0]` 整体跳过 |
| 直接导入法（绕过面板，远期） | `[IPress,Tool:Texture Map:TextureMap]` → `[FileNameSetNext]` → `[IPress,File:Texture:Import]` → `[IClick,6207]` | marcus_civis 2012 提供，可避免面板载入；翻转机制未验证，暂不采用 |
| ~~`Tool:Layers:Intensity` vs `Layer Intensity`~~ | ✅ 已定案（probe4d1/4h，见 §七 8.5） | `Layer Intensity`=真实强度（选择式）；`Intensity`=UI 假操作弃用 |
| ~~图层录制状态读/切（P0 生死验证）~~ | ✅ 已实测（probe2/4k） | bit0=录制；方案A 录制导入可行；实现避开 W-25 防误触 |
| ~~图层可见性/启用控制~~ | ✅ 已实测（probe4g/4i/4k） | 可见性 IClick(W-5) 闭环；启用态不还原 |
| 图层完整性链路（P4） | 多 Layer 往返（0.8.0 T4/T5） | 名称/顺序/强度/可见 全部还原（启用不还原） |

> 范围类数据（§2 表中"待实测"列）与上述未决路径**不写入本文档作为固定值**，实测确认后再回填更新，保持文档"固定且稳定"。
