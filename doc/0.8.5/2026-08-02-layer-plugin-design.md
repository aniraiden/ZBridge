# ZBridge 0.8.5 — 雕刻图层导出/导入还原 单功能插件设计规格

> 日期：2026-08-02
> 状态：**已批准执行**（用户确认）
> 基线：0.8.0 主程序（git commit `90d5399`）
> 定位：从 0.8.0 T4 长期未通过的图层导入还原功能中**彻底解耦**，单独开发一个只做"子工具图层导出 + 导入还原"的独立插件，验证成功后再并入主程序。
> 配套文档：`doc/0.8.5/PROGRESS.md`（分步结论记录）、`refrenece/knowledge/`（ZScript 知识库，移植阶段依赖）、`doc/zscript_python_reference.md` §7（图层实测定案）。

---

## 一、背景与问题定性

### 1.1 历史

- 0.8.0 T3（导出侧图层快照）已实现并通过初步测试（文件齐全、无闪退）。
- 0.8.0 T4（导入侧还原）已实现但**长期未通过测试**。
- 用户补充的关键信息：**导出的层快照 goz 本身就是"多个层的叠加态"**——问题从导出侧就开始了，不只是导入侧。

### 1.2 问题定性（本设计的前提假设）

1. "逐层快照的隔离性"从未被真正验证（T3 只验证了文件齐全，没验证每个 goz 是否只含单层形变）。
2. 叠加态 → delta 计算错误 → 导入重建全错。**隔离性是整个方案的地基**。
3. 0.8.5 的第一要务：用机器可判定的方式验证隔离性，若隔离不可能则整个 delta 方案必须更换。

### 1.3 已确认的用户决策

| 决策点 | 结论 |
|--------|------|
| 最终交付形态 | **ZScript 插件**（兼容 2025/2026 全版本，并入主程序） |
| Python 定位 | **快速验证原型**（ZBrush 2026+，CPython 3.11.9），机制验证 + 算法定型，不替代最终产物 |
| 处理范围 | **单子工具聚焦**（当前活动子工具） |
| 开发方式 | 从头规划，按本规格执行，不改来改去 |
| 备份 | git 基线 commit（已完成） |
| 测试策略 | **交叉对比**：少量测试、单次运行产出多个相互印证的指标 |
| 目录 | 保持整洁，成果记录可续档 |

---

## 二、目录规划

```text
ZBridge/
├── .git/                        # 基线备份（已 commit 90d5399）
├── .gitignore                   # 排除 debug.log / __pycache__ / *.pyc / prototype_py/log/
├── doc/0.8.5/
│   ├── 2026-08-02-layer-plugin-design.md   # 本规格
│   └── PROGRESS.md              # 分步结论记录（续档入口）
├── prototype_py/                # Python 原型
│   ├── zbridge_085.py           # 单文件：日志系统 + goz 解析 + 导出/导入流程
│   ├── probes/                  # 丢弃式探测脚本（每 spike 一个）
│   │   ├── probe1_isolation.py  # S1 隔离性
│   │   ├── probe2_record_import.py  # S2 录制导入
│   │   └── probe3_restore.py    # S2 恢复算法
│   └── log/                     # 运行日志（gitignore）
├── src/zscript/ZBridge_085.txt  # 最终 ZScript 单功能插件（S4 产出）
└── tests/                       # 既有测试保留不动（历史成果）
```

---

## 三、Python 日志系统（验证自动化的核心）

### 3.1 能力前提（已核实）

- ZBrush 2026.1 Python 运行时 = 标准 CPython 3.11.9。
- 完整文件 I/O、`os`/`struct`/`json` 标准库可用。
- **红线**：不用 `subprocess`/`multiprocessing`（会拉起新 ZBrush 实例导致崩溃）；不覆写 stdout/stderr stream handler（ZBrush 控制台重定向专用）。

### 3.2 日志设计

- 每轮运行写 `prototype_py/log/zb085_YYYYMMDD_HHMMSS.log`。
- 行格式：`[HH:MM:SS.mmm] [模块] 事件=值`。
- **每读每写都落日志**：层名/强度/可见位/录制位/文件存在性/顶点数。
- **自动断言**：关键步骤后内置校验（层数符合预期、录制位=1、delta 非零/零、文件存在），失败即 `[FAIL]` + 中止该阶段。
- 控制台 `print` 同步输出（不覆写 stream handler）。
- goz 解析：`struct` 直接读 POINT_LIST，计算 delta——"叠加态"由机器判定。

### 3.3 goz 解析要点

- 依据 `refrenece/goz_sdk/Sources/GoZ_Binary.h` / `refrenece/knowledge/08-goz-format.md`。
- 只读 POINT_LIST（顶点坐标）即可满足验证需求，不改写文件。
- 顶点数一致性：所有快照的 vertexCount 必须相等（拓扑校验）。

---

## 四、阶段设计

### S0 备份与目录规划 ✅ 已完成
git init + .gitignore + 基线 commit `90d5399`。

### S1 隔离性 Spike（最先做，方案生死判定）

**目标**：回答"逐层强度 1 + 其余 0 → 导出 goz 是否只含该层形变"。

**流程**（单次运行，交叉产出 5 项指标）：

已知原始状态：LayerA@1.0、LayerB@0.5 → 当前网格 `M = B + 1.0·dA + 0.5·dB`（B=基准，dA/dB=各层形变）。

1. 先导出当前态 `current.goz`（= M，作为恒等式右端基准）。
2. 归零全部 → 导出 `base.goz`（= B）。
3. 逐层（开眼 → 置 1 → 导出 `L_i.goz` → 置 0）：`L0.goz`（= B+dA）、`L1.goz`（= B+dB）。
4. Python 读全部 goz 顶点，逐顶点自动判定：

| 指标 | 恒等式/判定 | 交叉验证的意义 |
|------|------------|---------------|
| **A 线性叠加恒等式**（最强） | `delta(L0-base) + 0.5·delta(L1-base) == delta(current-base)`（逐顶点，误差<ε） | 同时验证隔离性 + 强度线性 + 基准纯净，任一污染即等式破坏 |
| **B 单层隔离** | `delta(L0) ≠ delta(L1)` 且均非零 | 两层形变互异，非全层叠加 |
| **C 强度线性** | `delta(L0)` 的量级与 `0.5·delta(L1)` 的量级比值 ≈ 2 | 强度语义正确（0-1 域线性） |
| **D 叠加来源定位** | 等式失败时，检查 `delta(L0)+delta(L1)-delta(current-base)` 的残差模式 | 残差 = 常数 → 基准污染；残差 = 某层形状 → 层序累计；随机 → 机制错乱 |
| **E 拓扑** | 全部文件 vertexCount 一致 | 顶点对齐前提成立 |

**三结局**：
- **隔离成立 ✅** → S2 继续。
- **部分叠加** → 日志定位引入叠加的步骤（归零残留？可见性阻断？层序？），修流程后重跑。
- **完全叠加** → 隔离不可能，delta 方案作废，进入分支：MDD 方案 / 录制采样 / C++ 合并网格（重新评估，不沿用 0.8.0 旧结论）。

**交叉对比价值**：A/B/C/D 单次同时产出，任何一对矛盾（如 A 过但 B 不过）直接指出是"强度机制"还是"层序累计"的问题。

### S2 录制导入 + 恢复算法 Spike

**probe2（录制导入）**：干净网格 → New（录制）→ 导入 `L_i.goz` → 退录制 → 断言：
- 新层形变 = delta_i（与 S1 的 delta 数据**交叉对比**）
- 基网格不变、旧层保留、录制位退出成功。

**probe3（恢复算法）**：完整模拟导入侧——归零 → 逐层建 → 强度/可见性/命名/顺序恢复，每属性读回断言。
- **交叉对比**：probe3 的期望值 = S1 导出的 layers.txt 记录值，数据链闭环。

### S3 Python 全功能原型

- `zbridge_085.py` 提供 `export(subtool)` / `import(subtool)` 两入口（单文件，符合项目偏好）。
- 端到端：导出 → 新会话导入 → 逐项断言 → 输出 `VERIFIED` 报告。
- 导出流程对齐主程序 T3 但**单子工具简化**（无多子工具/文件夹/贴图/动态细分交叉）。
- 导入流程对齐 T4 顺序定案（细分还原 → 切最高 SDiv → 逐层录制导入 → 切回）。

### S4 ZScript 移植

- 产出 `src/zscript/ZBridge_085.txt`：独立单文件插件，ZPlugin 菜单两按钮（Layer Export / Layer Import）。
- 1:1 翻译，依赖知识库与 project_memory 陷阱清单：

| ZScript 陷阱（必须遵守） | 依据 |
|--------------------------|------|
| `FileNameSetNext` 路径正斜杠拼接（反斜杠 → 缩放 ~70%） | probe4aM |
| `StrExtract` 第三参数 = 终点索引（含） | T3 根因 |
| 字符串判等用 StrLength+StrFind 双向前缀模式 | probe6 根因 |
| `[Delay,N]` 单位是秒（整数 Delay=假卡死） | probe6 根因 |
| `[If]` then/else 必须是单语句 | probe6 |
| 内存记录 null-terminated | 0.8.0 闪退根因 |
| 变量 camelCase 无下划线 / UTF-8 BOM + CRLF | 硬约束 |
| 位运算只在 If 条件；赋值用 If+加减 | 硬约束 |
| 空层列表先 `IsEnabled(Layer Intensity)` 再碰 Scrollbar | T3 闪退根因 |

- 测试：与 Python 完全一致场景，对照 VERIFIED 报告核对。

### S5 并入主程序

- **条件**：ZScript 版通过同等场景测试。
- 方式：例程并入 `src/zscript/ZBridge.txt`（升 0.8.5），复用/重构 0.8.0 挂接点。
- `prototype_py` 保留作回归基准。

---

## 五、风险与分支

| 风险 | 影响 | 对策 |
|------|------|------|
| 隔离性不可能（强度无法单层隔离） | delta 方案作废 | S1 最先验证；分支方案（MDD/录制采样/C++）重新评估 |
| Python 与 ZScript 命令行为差异 | 移植失真 | 同一套 UI 命令，Python 仅语言层增强；移植用对照表逐条核对 |
| 录制导入不可靠 | 导入重建失败 | S2 probe2 先验证；失败则探明原因（同 0.8.0 教训：假象 vs 真失败） |
| goz 顶点顺序不一致 | delta 套错 | 全部快照校验 vertexCount；不一致即 [FAIL] |

## 六、验收标准（S5 前置）

1. S1：隔离性判定为"成立"且 delta 数学关系自洽。
2. S2：录制导入形变=delta；恢复算法逐属性读回一致。
3. S3：Python 端到端 VERIFIED 报告全绿。
4. S4：ZScript 版通过相同场景，报告与 Python 一致。
