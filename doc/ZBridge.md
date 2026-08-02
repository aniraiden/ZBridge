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
| 第四阶段 | Active Tool、Material、Compatibility Layer | 待实现 |

> 版本策略：每个新功能发布时递增版本号（如 0.6.0、0.7.0…），保留前一版 release 存档。

## 十三、项目边界

本项目明确不负责：ZTL 解析 / 修改 / 降级、GoZ SDK 开发、第三方软件桥接、Mesh 编辑、Geometry 运算。

## 十四、核心思想

职责划分：**GoZ 负责几何数据，ZBridge 负责工程状态。**

> 两者职责清晰，不重复保存数据，不解析 ZTL，仅通过官方 GoZ SDK 实现 ZBrush 高版本到低版本的自动恢复。
