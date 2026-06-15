# AGENTS.md

Always respond in Chinese-simplified.

## 分支定位

这是 `gold-annotation` 的孤儿分支 `claude/rp-system`，只服务赫萝角色扮演系统层的"关系第一公民"新架构（见 `架构笔记.md`）。不重建原分支的大语料**流水线**（units 抽取脚本、phase2、casts 处理）和旧 `rp/` 草稿；
**正典正文可按需取小切片写成锚点记录**（数据层按需外接、不常驻、不重建管线）。

## 当前主线：写锚点笔记（subagent 工作区 = `anchors/`）

本轮唯一的进行中工作是逐卷写正典锚点笔记，工作环境是顶层 `anchors/`。完整规程见 `anchors/README.md`，这里只定 subagent 的用法和边界。

**目录分工：**

- `anchors/extract/claude/` 与 `anchors/extract/codex/`：两个**真模型臂**各自的原始锚点。Claude 臂走 Claude Code subagent，工作目录固定在 `anchors/extract/claude/`；Codex / GPT-5.5 臂是外部真模型，落在 `anchors/extract/codex/`。
- `anchors/notebook/`：跨臂**对比/合并**后的产物。卷01–03 是这套双臂流程之前的早期合并稿，留作对照。
- `anchors/extract/` 抽取脚本辅料也放这层下。

**subagent 怎么用（仅限锚点笔记的 Claude 臂）：**

1. 一卷一个 subagent，工作区限定 `anchors/extract/claude/`，**一步通读整卷**（先用 `canon/tools/canon_slice.py` 切片，不裸读 JSON），在一步内完成"选范围 + 精读 + 写锚点"，不预选范围、不分多次喂。仅当某卷长到一步通读不可靠时，才先生成客观分幕目录（只列 scene 摘要，不判"算不算关系锚"）。
2. **范围留痕是一等输出**：锚点开头显式标注主轴 scene / 只读梗概段 / 为什么这么切 / 用的切片命令，并能回指 `canon/maintext/卷NN.json`。范围决策不进黑箱，方便对比时第一刀并排比两臂的切法。
3. **两臂独立、不共享中间结果**。Claude 臂的 subagent 不得读 codex 臂的产物再写，反之亦然——保住两个真模型的异质对比。**严禁用 subagent 顶替 codex 臂**（同源会制造"已交叉验证"的假象）。
4. subagent 只产出事实观察、暂时读法、暂存弱模式（弱模式须标临时/带条件/非定稿），**不定机制、不写 policy、不加字段化 frontmatter**（弱约束见 `anchors/README.md`）。
5. 跨臂对比与合并（README 第 4、5 步）从新 session 做，产物落 `anchors/notebook/`；裁决、升格机制候选、准入 gate、定稿一律由人来。

注意：这跟"被测/判定不用 subagent"的纪律（见教训 7）不冲突——那条管的是 eval 回路里的被测模型和判官；锚点笔记的 Claude 臂本来就是 Claude，用 Claude Code subagent 是同源一致，不是伪造交叉验证。

## 工作边界

- 架构骨架在 `架构笔记.md`：场景五元组、关系三字段（关系位置/trust 档/关系内压强）、相图、目的层分离。改架构先改它。
- 测试/对比资料在 `tests/exp4/`：只保留 exp4 的冻结探针、runtime 投影和结果档；冻结文件（`*.frozen.md`、runs、runtime 投影）只读，不得改写。
- `bible/` 是机制定稿区 + 归档，不是 active 圣经：逐场锚点记录已提到顶层 `anchors/`（当前主线）；后续锚点足够厚时才进入跨锚综合，并可从 `bible/archive/synthesis/` 取回旧候选重审；最后才到 `bible/policy.md` 人定稿。旧 Lore 等草稿在 `bible/archive/`，不得作为 prompt 或机制依据直接复用。
- active 圣经/prompt/eval 三件套尚未落地；首笔 active 版本必须同 commit 出现（机制正文 + prompt 组装 + eval 输入/协议口径）。
- 数据层按需外接，不在本分支常驻。
- 读取正典（`canon/`）必须通过 `canon/tools/canon_slice.py` 切片，不得裸读 JSON 后大段贴入上下文。脚本按卷/scene 范围切片、只返回锚点记录所需的最小窗口。

## 过去实验的教训（把握精神，不必拘字面）

下面是前几轮实验踩出来的教训，不是不可违反的戒律——情境变了就按精神调整，并更新本表：

1. 裸基线优先：任何圣经改动都要能和 `bare` 对比（同模型同参数，唯一变量=圣经）。
2. fit/validate 分离：round1/round2 只作回归锚；holdout 须是新圣经 commit 后独立出题的 round3。
3. 不把"像不像原文"当优化目标——但**从正典锚点记录提取生成过程**是冷启动正道（≠表面模仿）；贴近正典的表层只作警报和锚点。
4. 机制要写成可迁移的生成过程，并标支持场景与复杂化反例；不要停在"骄傲/聪明/嘴硬"这种标签层。
5. 圣经机制正文由人定稿；Claude 采正典、写锚点记录、做跨锚结构化追踪、给正典锚定的候选抽象（辅助论证与评测），不凭空替人拍板机制。
6. 关系对象加字段须过准入测试（架构笔记 §0）：能构造最小翻转探针对才准入；intimacy、conflict residue 已否决，防回潮。
7. **eval 回路**的被测与判定走云 API 直调，不用 subagent（harness 提示词污染上下文）；模型版本与采样参数记进 runs。注：写锚点笔记的 Claude 臂用 subagent 不在此列（见上"当前主线"）。
8. 新增目录前先在 README 目录表声明职责，避免重新长成杂物堆。
