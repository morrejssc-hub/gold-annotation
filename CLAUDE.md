# AGENTS.md

Always respond in Chinese-simplified.

## 分支定位

这是 `gold-annotation` 的孤儿分支 `claude/rp-system`，只服务赫萝角色扮演系统层的"关系第一公民"新架构（见 `DESIGN.md`）。不要把原分支的大语料流水线、正文 JSON、casts、phase2、units、旧 `rp/` 草稿或历史实验重新搬回来，除非用户明确要求。

## 工作边界

- 架构骨架在 `DESIGN.md`：场景五元组、关系三字段（关系位置/trust 档/关系内压强）、相图、目的层分离。改架构先改它。
- 测试/对比资料在 `tests/exp4/`：只保留 exp4 的冻结探针、runtime 投影和结果档；冻结文件（`*.frozen.md`、runs、runtime 投影）只读，不得改写。
- 圣经/prompt/eval 三件套尚未创建；首笔落地三者必须同 commit 出现。
- 数据层按需外接，不在本分支常驻。

## 不能违反的纪律

1. 裸基线优先：任何圣经改动都要能和 `bare` 对比（同模型同参数，唯一变量=圣经）。
2. fit/validate 分离：round1/round2 只作回归锚；holdout 须是新圣经 commit 后独立出题的 round3。
3. 不把"像不像原文"当优化目标；贴近正典只作警报和锚点。
4. 机制要写成可迁移的生成过程，并标支持场景与复杂化反例；不要停在"骄傲/聪明/嘴硬"这种标签层。
5. 圣经机制正文由人写；Claude 辅助论证与评测，不直接生成机制。
6. 关系对象加字段须过准入测试（DESIGN §0）：能构造最小翻转探针对才准入；intimacy、conflict residue 已否决，防回潮。
7. 被测与判定走云 API 直调，不用 subagent（harness 提示词污染上下文）；模型版本与采样参数记进 runs。
8. 新增目录前先在 README 目录表声明职责，避免重新长成杂物堆。
