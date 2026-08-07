# 0.8.5 进度记录（续档入口）

> 阅读顺序：**先看本文件** → 结论与下一步 → 需要细节再看 `2026-08-02-layer-plugin-design.md`（规格）。
> 规则：每完成一个阶段，把结论写进"结论记录"；每发现新事实/陷阱，追加到"实测事实"。

## 阶段状态

| 阶段 | 内容 | 状态 | 结论 |
|------|------|------|------|
| S0 | 备份与目录规划 | ✅ 完成 | git commit `90d5399`；.gitignore 就绪 |
| S1 | 隔离性 spike | ✅ 完成 | **隔离成立**：A 残差 5.96e-08（浮点级）、B/E PASS；7938 顶点 |
| S2 | 录制导入 + 恢复算法 spike | ✅ 完成 | **录制导入成立**（probe2）+ **恢复算法全绿**（probe3 v6：三网格残差 0.000000） |
| S3 | Python 全功能原型 | ⬜ 补场景验证中 | 2 层 e2e 已 PASS（08:40）；场景3 真实探测两轮：第1轮（093838/094158）三问题已定位修复（顺序=非bug+按名设状态/rename 封禁留S4/MoveUp 核对）、第2轮（095353）根因=重建细分使顶点数不匹配→Tool:Import 替换工具（已 fail-fast + 指引修正"不重建细分"）；导出段已改"不设状态、导出前后比对"；重建细分方案=Reconstruct Subdiv（探测脚本 probe_reconstruct_sdiv.py 待用户试验） |
| S4 | ZScript 移植 | ⬜ 未开始 | — |
| S5 | 并入主程序 | ⬜ 未开始 | — |

## 结论记录

### S3 场景3 补验证（2026-08-03，用户三轮反馈 → 两轮真实 ZBrush 探测）
- **第1轮（093838 export / 094158 import / 093612 probe_rename）**：
  - ① "顺序反了"**非 bug**：`Layer<i>.goz` 的 i = layerIndex（0=最底层），与视觉堆叠顺序无关；用户文件栈顶=LayerA/栈底=LayerC → Layer0=LayerC 完全符合规则。真实问题：旧探测脚本**按位置设状态**（假设 LayerA 栈底）→ 用户层序相反 → 设错层（LayerC 0.2→1.0）。修复：export 段改**按层名匹配**设状态（`_goto_named`）。
  - ② **`Tool:Layers:Rename` 弹模态框"enter layer title"阻塞脚本 30 秒**（probe_rename 日志 09:36:12→09:36:42，用户手动回车），`FileNameSetNext` 无效，SDK 无 Python DLL 调用能力 → **Python 侧封禁重命名**，`import_layers` 默认 `rename=False`；层名恢复列入 S4 ZScript 版（ZFU DLL）。用户表态：重命名不重要，无法实现就略过。
  - ③ **可见性核对误报**：重名层（全叫 Untitled Layer）按名寻址恒命中栈顶 → imported[1]/[2] 误读 vis=False（但网格残差 0.000000 证明实际恢复成功）。修复：核对循环改**逐层 MoveUp 到栈顶读取**。
- **第2轮（095353 import，用户按指引重建细分到 SDiv3 后跑）**：
  - **根因**：重建细分（Divide）使顶点数翻倍 → 录制导入时 goz 顶点数与当前网格**不一致** → `Tool:Import` **替换当前工具**（丢图层、丢细分，`tool_replaced`）；idx=0 失败后继续建层 → 后续层以"LayerC 网格"为录制起点 → delta 全污染为 `X−LayerC`（用户"基础模型变 LayerC、两层形状=LayerA/LayerB 和负的 LayerC"铁证）。
  - **修复**：① `import_layers` 遇 `tool_replaced` **fail-fast 中止**（不再继续建层污染）；② 指引修正——**导入段不需要重建细分**（goz 自带最终顶点，上轮 094158 无细分导入 3 层全成功、resid=0.000000 已验证；细分级别不参与网格恢复）。
- **导出段再修正（用户反馈"导出后改变了原状态"）**：probe 上一版故意设确定性状态导致用户层状态被改。**新方案：不设任何状态，直接导出用户原始状态 + 断言"导出后各层状态=导出前"**（before/after 逐层比对，层序不变由 export_layers 保证）。
- **重建细分方案（用户要求"既重建细分又导回层"，WebSearch 查证）**：
  - **方案 A（推荐）· Reconstruct Subdiv**：对导入的 goz 网格（无细分历史，只要是标准细分生成的四边形拓扑）按 Geometry→Reconstruct Subdiv 可从**最高级网格反推创建低级别，最高级顶点数不变**（ZBrushCentral Pixolator/marcus_civis 官方解答）→ 最高级顶点=各层 goz 顶点 → 录制导入顶点匹配 → 不替换工具。已写探测脚本 `probe_reconstruct_sdiv.py`（自动按至 SDiv 3 并记录每步 max）。
  - **方案 B（备选）· GoZ Complete Binary**：相同拓扑在最低级导出/导入可保留细分级别（Marcus Civis 2017 Transfer Pose），但该格式 gozlib 无法解析，需扩展，暂不采用。
  - **ZBrush 图层+细分规则**（ZBC 2019 笔记）：有细分级别时图层选项（merge/record 等）**必须在最高级才可用**——导入段本就在最高级操作 ✓。
- **mock 现状**：4 场景全绿（2 层 / 3 层+强度+重命名+SDiv / 顶点不匹配 fail-fast）。MockZBC 新增"顶点数不匹配→替换工具"模拟。

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
- **2026.1 滑杆强度从 0 设到 >0 会自动开眼**（0.8.0 主程序注释"强度>0 不会自动开眼"已过时）。铁证：导出日志 23:47:02 LayerA 快照后置 0 → 恢复 set 1.0 → 紧接着 `click_eye want=False`（IModGet 读到自动开眼，对称点击关闭），after_export 确认 LayerA@1 隐藏成立——证明"强度1+隐藏"可达，也证明设 1.0 确实自动开眼。
- **导入后层名全是 "Untitled Layer"（重名）**：按名寻址（IClick/IModGet/click W-25/W-5）恒命中栈顶，任何"事后原地恢复 pass"对非栈顶层必然误操作。**解法：可见性在 build 阶段设置（此时本层=栈顶=首匹配，按名寻址唯一安全）；强度因录制隔离必须推迟到恢复 pass，用"SelectDown 到栈底 → MoveUp 到栈顶 → 操作"逐层处理（目标层移到栈顶后按名寻址才安全）**（见"录制起点污染"条目）。
- **S3 导入段 CHECK 根因**（2026-08-02 23:51 两轮复现）：`import_layers` 旧恢复 pass 只设强度、不碰可见性 → LayerA（记录 vis=False）强度 0→1 自动开眼后被误留可见 → `final = base + dA + dB`（全计残差 0.000000）、用户肉眼两层均可见。旧 pass 另有一处顺序错位（`built_recs` 为栈底→栈顶，却从栈顶开始导航），因两记录强度同为 1.0 被掩盖。**最终修复见下条"录制起点污染"（build 只做可见性、强度恢复 pass 用 MoveUp 机制）。**
- **录制起点污染**（2026-08-03 08:33 实测）：`New` 的录制起点 = **New 按下瞬间的当前网格**（含所有可见层贡献）。若建层时就把目标强度设上，后建层的 delta 被污染为 `dA−dB`（用户肉眼"第一层形状=LayerA 和负的 LayerB 的叠加"即铁证）；该层若隐藏则最终网格仍正确（e2e 判定 PASS，数据已错）。**修复定案：build 阶段强度保持 0（录制隔离），强度统一由恢复 pass 设置；恢复 pass 每层先 SelectDown 到栈底再 MoveUp 到栈顶后操作（重名层按名寻址恒命中栈顶，必须把目标层移到栈顶才安全），从 idx 最小开始、处理完保留栈顶，层序自然复原。** mock 已补"录制起点=New 时当前网格"模拟（`MockZBC._rec_start`），能捕获此回归。
- **录制导入顶点数不匹配 → Tool:Import 替换当前工具**（2026-08-03 095353 实测）：在录制模式下 `Tool:Import` goz，若 goz 顶点数与当前网格**不一致**（如 Divide 重建细分使顶点翻倍），ZBrush **整体替换当前工具**（丢图层、丢细分；`layer_build_snapshot` 判定 `tool_replaced`）。之后继续建层会在被替换的网格上录制 → delta 污染为 `X−LayerC` 型。**修复：`import_layers` 遇 `tool_replaced` fail-fast 中止**；**正确顺序 = 不重建细分**（goz 自带最终顶点，导入 LayerBase.goz 后网格即最终形态，顶点与各层 goz 天然一致）。
- **`Tool:Layers:Rename` Python 侧封禁**（2026-08-03 probe_rename 实测）：`FileNameSetNext` + `Tool:Layers:Rename` 弹模态框"enter layer title"阻塞脚本约 30 秒，set_next_filename 无效（`got=LayerA ok=False`），Python SDK 无 DLL 调用能力 → **层名恢复留 S4 ZScript 版（ZFU DLL RenameSetNext）**；`import_layers` 默认 `rename=False`。用户表态：重命名不重要，无法实现就略过。
- **Reconstruct Subdiv 可对导入网格反推低级别**（WebSearch 2026-08-03 查证）：ZBrush 的 Geometry→Reconstruct Subdiv 对"标准细分生成的四边形网格"（含导入的无细分历史网格）可从最高级**反推创建更低级别，最高级顶点数不变**（ZBrushCentral Pixolator 2004 / marcus_civis 2009 官方解答；限制：不能含三角形、多边形数须能除4）。→ 顶点数不变的细分重建方案（配合"图层操作须在最高级"规则）。


## 下一步行动

1. **S3 场景 3 补验证（进行中，用户要求 S4 移植前先全部在 Python 验证）**：
   - 已落地修复：export 段不设状态+前后比对（LayerC 0.2 可见应保持不变）；`import_layers` rename=False（不弹框）+ `tool_replaced` fail-fast；核对 MoveUp 读栈顶；mock 4 场景全绿。
   - **请你按序跑**：① `probe_e2e3_export.py`（验证"导出后状态=导出前"）→ ② 新会话导入 out/<subtool>_LayerBase.goz → ③ `probe_reconstruct_sdiv.py`（Reconstruct Subdiv 重建细分，验证最高级顶点数不变的方案）→ ④ 切回最高 SDiv 后 Load `probe_e2e3_import.py`（应在 SDiv 3 上导入层，顶点匹配不替换工具）。日志在 prototype_py/log/，我读取分析。
   - Reconstruct Subdiv 若无效（max 不增），备选：GoZ Complete Binary 方案或接受"导入无细分"。
2. 全部 PASS 并经你确认后再开始 S4 ZScript 移植（层名恢复用 ZFU DLL；S4 需要先查主程序 ZFU 接口）。
