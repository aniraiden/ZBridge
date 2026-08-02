# 0.8.5 进度记录（续档入口）

> 阅读顺序：**先看本文件** → 结论与下一步 → 需要细节再看 `2026-08-02-layer-plugin-design.md`（规格）。
> 规则：每完成一个阶段，把结论写进"结论记录"；每发现新事实/陷阱，追加到"实测事实"。

## 阶段状态

| 阶段 | 内容 | 状态 | 结论 |
|------|------|------|------|
| S0 | 备份与目录规划 | ✅ 完成 | git commit `90d5399`；.gitignore 就绪 |
| S1 | 隔离性 spike | ✅ 完成 | **隔离成立**：A 残差 5.96e-08（浮点级）、B/E PASS；7938 顶点 |
| S2 | 录制导入 + 恢复算法 spike | ✅ 完成 | **录制导入成立**（probe2）+ **恢复算法全绿**（probe3 v6：三网格残差 0.000000） |
| S3 | Python 全功能原型 | ⬜ 未开始 | — |
| S4 | ZScript 移植 | ⬜ 未开始 | — |
| S5 | 并入主程序 | ⬜ 未开始 | — |

## 结论记录

### S0（2026-08-02）
- 基线备份：`git init` + 全部文件 commit `90d5399`（含主程序 v0.8.0、releases、tests、doc、refrenece）。
- .gitignore：排除 `debug.log`、`__pycache__/`、`*.pyc`、`prototype_py/log/`。
- 目录：新建 `doc/0.8.5/`、`prototype_py/` 骨架；`tests/` 既有文件不动。

### S1（2026-08-02，probe1 真实 ZBrush 运行 + 机器判定）
- **结论：图层隔离性成立，强度滑杆线性（0-1 域）实锤**。
- 真实数据：cur/base/L0/L1.goz 各 7938 顶点；`A_pass=True`（残差 5.96e-08）；`B_isolated=True`（dA=0.973、dB=0.887）；`D1=D2=0.4436`（恰为 0.5×dB，与 LayerB@0.5 精确吻合）。
- 数值模型定案：`current = base + Σ intensity_i × delta_i`（delta_i = Layer_i@1 - base）。
- 眼图标点击**有效**（L0/L1 均抓到真实形变）；但点击后立即 IModGet 读取滞后（`now=False` 假象），已从日志中移除该读回、不设状态门。
- 过程 bug：gozlib 用 `GOZ_TAG_POINT_LIST=10000`，真实 ZBrush 写 `10001`（C 枚举 BASE_ID+1）→ 首跑假阳性 `counts=[0,0,0,0]`；修复后回归测试 + 真实文件可选回归测试（`out/cur.goz` 存在时）双保险。

### S2 录制导入（2026-08-02，probe2 真实 ZBrush 运行 + 机器判定）
- **结论：录制导入成立**。`New(自动录制) → 导入 L0.goz → 退录制` 后：层数 0→1、rec=False、网格形变与 S1 的 delta(L0) **残差 0.000000**（精确）。
- 录制语义定案：**层 delta = 导入网格 − 录制起点网格**（起点 = New 按下瞬间的网格）。由此修正 probe3 恢复算法：每建一层前必须归零，否则后建层 delta 被污染为 dA−dB。
- New 默认层名 "Untitled Layer N"（命名恢复留到 ZScript 版 ZFU）。

### S2 恢复算法（2026-08-02，probe3 v3→v6 迭代 + 用户肉眼 + 机器判定）
- **结论：恢复算法全绿**。probe3 v6 四项断言全部 PASS、三网格残差 **0.000000**：
  - `a_diag` = base+dA（第二次 New+导入捕获 dA 且 A 开眼参与合成）
  - `restore_full` = base+dA+dB（双录层重建成功）
  - `restore_top0` = base+dB（A 置 0 后仅剩 B 贡献）
  - 强度写读往返 0.5↔0.5；层数=2
- **v5 根因（同名层陷阱）**：IGetTitle 对两层均返回 "Untitled Layer"（UI 显示 "Untitled Layer 1/0" 但 IGetTitle 读不到数字），名称路径 `Tool:Layers:Untitled Layer` **恒命中首匹配 = 调色板列表第一行（栈顶）**；v5 全部 W-25/W-5 点击、get_mod 读全落第一层，第二层录制从未退出、眼从未打开 → 网格只有 base+dB。用户肉眼"第二层形状=LayerA"证实内容其实录进了层（Import 作用于当前层不走名称路径），只是从未参与合成。
- **v6 方案（恢复算法定案）**：**不依赖命名**，用 **MoveUp/MoveDown 重排 + 首匹配寻址**：
  1. 建 B（唯一层，首匹配=B）→ W-25 退录制 ✓
  2. 归零 B（滑杆，当前层）
  3. 建 A（New 插栈底）→ MoveUp A 到栈顶 → 首匹配=A → W-25 退录制 + 开眼舞步 ✓
  4. 需要 B 时 SelectDown→MoveUp B 到栈顶
  5. 强度全走滑杆（当前层，选择式寻址，重名免疫）；开眼舞步 = 置 0（自动关眼）→ IClick W-5 → 恢复强度（零读依赖）
- v6 过程 bug：`_classify` 元组解包顺序写反（`(residual,name)` 被解为 `name,resid`）→ 首个网格断言 ValueError 中止；修复后全绿（提交 4f006e8）。
- W-25 退录制点击后**立即读回 rec 位可能滞后**（A 的读回 True→80ms 后 False；与 S1 "点击后 IModGet 滞后"一致）→ 退录制**不做 rec 读门**，以层存活计数 + 最终网格真值为准。

## 实测事实（新发现，随时追加）

- **ZBrush 2026.1 无 Python 交互控制台**：脚本通过 ZScript 面板 → *Python Scripting* 子面板 → **Load** 按钮加载即执行（Reload 重跑上次脚本）；命令行方式为 `ZBrush.exe -script "script.py"`（ZPR 文件放最后参数）。控制台输出需在 *Script Window Mode* 切 *Python Output* 模式（官方 quickstart 2026-08-02 查证；日志文件才是主反馈通道）。官方 hello_world 示例确认标准 `if __name__ == "__main__"` 保护约定。
- **IClick/IModGet 按"名"解析（首匹配）**：`Tool:Layers:<name>` 类路径命中调色板列表第一行（栈顶），与点击坐标/几何无关；同名层全部操作落栈顶（v5 全中招），唯一名层按名精准解析（probe1 的 LayerA/LayerB 在非顶层也能开眼成功）。**W-5/W-25 点击只对"行内位置"有意义（W-5=眼、W-25=退录制），对"哪一行"无意义。**
- **滑杆 `ISet/IGet(Tool:Layers:Layer Intensity)` = 当前选中层**（选择式寻址，重名免疫）——v6 日志中 B/A 在非顶层读到各自的 int（0.0/1.0）即铁证。
- **主程序 T3 导出后调用 ZBRunLayerRestoreMem 恢复原强度+可见性**（ZBridge.txt L805-806）；恢复顺序 = 先强度后可见性、期望与当前不一致才点击（对称恢复原型层用 layer_set_visible 双向）。
- **主程序 T3 逐层快照循环**：全部归零 → 导出 LayerBase → 从栈底向上逐层（开眼→置1→导出 Layer<j>→置0→SelectUp）；`Layer<j>.goz` 的 j 即 layerIndex（0=原始栈底层）。
- **T4 建层顺序 = layerIndex 升序**（0=栈底先建），但主程序注释"New 总插栈顶"与 2026.1 实测（**New 插栈底**）矛盾——正是 T4 长期失败的嫌疑点之一；0.8.5 原型已按实测重写（v6 MoveUp 机制）。


## 下一步行动

1. **S3 端到端（进行中）**：`probe_e2e.py` 两段运行——第一段 export（当前子工具须 2 层，设确定性状态后 export_layers + 脚本内自检快照/记录），第二段 import（新会话导入 `<subtool>_LayerBase.goz` 干净网格后 import_layers，导出 e2e_final 与期望网格比对输出 VERIFIED）。**本地 mock 端到端（test_zbridge_mock.py）已全绿**：记录/快照/重建层数/强度/可见性/最终网格六项闭环。
2. S4 ZScript 移植、S5 并入主程序。
