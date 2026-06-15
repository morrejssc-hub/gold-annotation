# AGENTS.md

Always respond in Chinese-simplified.

## 分支定位

这是 `gold-annotation` 的孤儿分支 `claude/rp-system`，只服务赫萝角色扮演系统层的"关系第一公民"新架构（见 `DESIGN.md`）。不重建原分支的大语料**流水线**（units 抽取脚本、phase2、casts 处理）和旧 `rp/` 草稿；**正典正文可按需取小切片写成锚点记录**（数据层按需外接、不常驻、不重建管线）。

## 工作边界

- 架构骨架在 `DESIGN.md`：场景五元组、关系三字段（关系位置/trust 档/关系内压强）、相图、目的层分离。改架构先改它。
- 测试/对比资料在 `tests/exp4/`：只保留 exp4 的冻结探针、runtime 投影和结果档；冻结文件（`*.frozen.md`、runs、runtime 投影）只读，不得改写。
- `bible/` 是机制工作区，不是 active 圣经：当前只做 `anchors/` 逐场锚点记录；后续锚点足够厚时，才进入跨锚综合并可从 `bible/archive/synthesis/` 取回旧候选重审；最后才到 `policy.md` 人定稿。旧 Lore 等草稿在 `bible/archive/`，不得作为 prompt 或机制依据直接复用。
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
6. 关系对象加字段须过准入测试（DESIGN §0）：能构造最小翻转探针对才准入；intimacy、conflict residue 已否决，防回潮。
7. 被测与判定走云 API 直调，不用 subagent（harness 提示词污染上下文）；模型版本与采样参数记进 runs。
8. 新增目录前先在 README 目录表声明职责，避免重新长成杂物堆。
