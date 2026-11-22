# ZBridge —— ZBrush 跨版本降级插件开发文档

## 一、项目目标

ZBridge 是用于**不同版本 ZBrush 之间工程迁移**的辅助插件。

> **唯一目标：让高版本 ZBrush 创建的 Tool 尽可能无损地迁移到低版本 ZBrush。**

例如：ZBrush 2026 → 2024、ZBrush 2027 → 2025、任意高版本 → 任意低版本。

本项目**不是**：GoZ 替代工具、Mesh 导入导出工具、第三方软件桥接工具、ZTL 文件解析器、ZTL 降级器。

项目完全建立在**官方 GoZ SDK** 之上。

## 二、设计原则

1. **绝不解析 ZTL/ZPR。** 所有数据均来自当前 Tool、GoZ SDK 与插件自身记录。
2. **GoZ 负责 Mesh。** Mesh、UV、Polypaint、Texture、Material、Geometry 全部交给 GoZ，插件绝不重复保存。
3. **manifest 仅保存 GoZ 无法表达的信息。** 如 SubTool 顺序、Folder、Visible、Active Tool、插件版本等，避免重复记录。
4. **Recovery Engine 是插件核心。** GoZ 负责恢复 Mesh，Recovery Engine 负责恢复 Tool 状态。

## 三、整体流程

```text
ZBrush 2026 --导出--> 导出目录（GoZ + manifest）--导入--> ZBrush 2024
```

整个流程无需同时打开两个 ZBrush。

## 四、插件功能

插件只有两个功能：**Export For Older Version**（导出）与 **Import From Newer Version**（导入），不提供其它复杂功能。

## 五、Export 模块

流程：读取当前 Tool → 遍历全部 SubTool → 导出 GoZ → 生成 manifest。

Export 职责：导出 GoZ、记录恢复信息。

## 六、Import 模块

流程：选择导出目录 → 读取 manifest → 循环导入 GoZ → Recovery Engine 恢复 Tool。

Import 职责：导入 GoZ、调用恢复引擎。

## 七、工程格式

导出产物是一个**目录**（无打包，ZIP 可由用户自行完成）：

```text
导出目录/
├── zbridge_manifest.txt   # 全部 SubTool 元数据
├── Body.goz               # 以子工具名命名
├── Hair.goz
└── ...
```

GoZ 文件以子工具名命名（`<子工具名>.goz`），与 manifest 同级平铺。

## 八、manifest

manifest 不保存 Mesh，仅保存 GoZ 无法表达的状态。每条记录为 9 个管道分隔字段、null 终止：

```text
colorize|maxSdiv|curSdiv|subtoolEye|folderEye|isFolder|isOpened|folderName|name\0
```

| 字段 | 含义 |
|------|------|
| colorize | 1=有顶点色，0=无 |
| maxSdiv / curSdiv | 最高 / 当前细分级别 |
| subtoolEye / folderEye | 子工具眼睛位（bit0）/ 文件夹眼睛位（bit1） |
| isFolder / isOpened | 是否文件夹 / 文件夹展开状态 |
| folderName / name | 所属文件夹名 / 子工具或文件夹名 |

## 九、Recovery Engine

Recovery Engine 为插件最重要模块，负责恢复：

- Tool 名称、SubTool 名称与顺序
- Folder 结构
- Visible 状态
- Colorize、细分级别

以后如需恢复 Material、Transform 等，均在此模块实现。

## 十、Compatibility Layer

Import 时检测目标版本，自动忽略低版本不存在的数据，不影响导入。

## 十一、插件模块

整个插件保持极简：

```text
ZBridge
├── UI                  # 两个按钮
├── Export              # 导出 GoZ、生成 manifest
├── Import              # 导入 GoZ、调用恢复
├── Recovery Engine     # 恢复 Tool / SubTool 状态
├── Compatibility Layer # 处理版本差异
└── Manifest            # 读写 manifest
```

## 十二、开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| MVP | GoZ 导出/导入、Tool/SubTool、名称、顺序 | ✅ 0.1.0 |
| 第二阶段 | Folder、Visible | ✅ 0.2.0–0.4.0 |
| 第三阶段 | 子工具重名检查（后续功能的前置） | ✅ 0.5.0 |
| 后续规划 | 动态细分预览与属性还原（8 属性，manifest ext 字段） | ✅ 0.6.0 |
| 后续规划 | 颜色贴图还原（贴图重新贴回，hasTexture/textureFile） | ✅ 0.7.0 |
| 后续规划 | 雕刻图层还原 | 待实现 |
| 后续规划 | Stager 阶段保留（Home/Target，ext stg* 键 + `<名>_StageAlt.goz`） | ✅ 0.9.0（待真机验证） |
| 第四阶段 | Active Tool、Material、Compatibility Layer | 待实现 |

> 版本策略：每个新功能发布时递增版本号（如 0.6.0、0.7.0…），保留前一版 release 存档。

## 十三、项目边界

本项目明确不负责：ZTL 解析 / 修改 / 降级、GoZ SDK 开发、第三方软件桥接、Mesh 编辑、Geometry 运算。

## 十四、核心思想

职责划分：**GoZ 负责几何数据，ZBridge 负责工程状态。**

> 两者职责清晰，不重复保存数据，不解析 ZTL，仅通过官方 GoZ SDK 实现 ZBrush 高版本到低版本的自动恢复。

## 十五、Stager 阶段保留（0.9.0）

Stager（Tool > Geometry > Stager，ZBrush 2018 起）为每个子工具保存 Home Stage / Target Stage 两个摆位。GoZ 只携带当前摆位，所以由插件补全另一阶段：

- **导出**：主 GoZ 导出后（仍在最高 SDiv、Dynamic 预览已关），若 Switch Stage 可用（两阶段齐全）：Switch Stage → 导出 `<名>_StageAlt.goz` → Switch Stage 切回 → 把刚导出的主 GoZ 导回（保证导出不改动场景）。ext 追加 `stg=1;stgHome=;stgTarget=;stgCur=0;stgAlt=;stgCount=;`。
- **导入**：Phase 2 内、**Reconstruct Subdiv 之前**（此时网格与 StageAlt 顶点顺序一致，Import 只更新顶点；之后再 Import 会整体替换网格、细分与阶段一起丢失）。当前网格存为 Home → 导入 StageAlt → 存为 Target → Switch Stage 回到 Home → 恢复 Stages Count。
- **兼容**：所有控件 `IExists` 防护；无 Stager 的低版本整体跳过；不含 stg 键的旧导出完全不受影响。

### 实测（ZBrush 2022.0.5，导出→导入同版本，tests 外的自动化脚本逐顶点比对）

| 检查项 | 结果 |
|------|------|
| 导出后源模型与导出前 | 完全一致（最大偏差 0） |
| 导入后当前摆位 vs 原 Home | 一致（最大最近邻偏差 1e-7） |
| 导入后 Switch 一次 vs 原 Target | 一致（1e-7） |
| 再 Switch 回来 vs 原 Home | 一致（1e-7） |
| 细分级别 / 显示级别 | 2 级 / 1 级，保留 |
| 无阶段的子工具 | 不受影响 |

### 控件读数（实测）与由此带来的限制

- Home/Target 的 `IGet`：0=未存，1=已存；Switch Stage 仅两阶段齐全时可用。
- **读不出当前在哪个阶段**（Switch Stage 的 `IGet` 恒为 0，`IModGet`/`IGetSecondary` 不支持）：导出时的当前摆位一律记为 Home。若导出时停在 Target，迁移后两个摆位都在、Switch 照常往返，只是 Home/Target 名称互换。
- **Switch Stage 是相对切换**：存阶段后又移动、未再存，导出后 Home=移动后的摆位，Target=它加上原 Home→Target 偏移（与在原文件里按 Switch 的结果一致），原先存的绝对 Home 位置不保留。
- Interpolate 生成的中间阶段不导出（导入后用 Stages Count + Interpolate 重新生成）。
- 含雕刻图层的子工具不做阶段迁移（导出不做 Switch 往返，导入跳过并在完成提示中计数）。
- 跨版本（如 2025 → 2022）尚未实测；控件路径相同，ZBrush 2024.4 文档截图中的按钮名称一致。
