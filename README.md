# 赫萝角色扮演系统层 · 关系第一公民架构

孤儿分支，从零开始的角色扮演系统层新架构。不携带原分支的语料工程流水线，不保留旧 `rp/` 草稿。

主线问题不变，但架构换骨：

> 以"关系"为第一公民的场景 schema + trust×压强相图 + 分离的目的层，能否让赫萝在正典之外的新场景里稳定、可辨认、且不违背机制地回应。

## 目录

| 路径 | 职责 |
|---|---|
| `DESIGN.md` | 架构骨架：场景五元组、关系三字段、相图区域、目的层纠偏、评测协议。圣经正文不在此。 |
| `tests/exp4/` | 旧 exp4 冻结探针（round1/round2 共 32 条）、v3.1 runtime 投影、已跑结果。只作回归锚与对照基线，不是 holdout。 |
| `pilot/model-selection/` | 被测模型选型 pilot：场景→目的推演入侵率测量。脚本 + 批量输入输出 + 判定报告。一次性实验，选型定稿后冻结。 |
| `tests/annotation/` | 纸面标注实验（DESIGN §7 step1）：32 条冻结探针按三轴（trust 档 / 关系内压强 / 环境压力）逐条标注，验 ①两维散开 ②相图区域复现判型。schema 证伪点，排在写圣经前。不改写冻结探针，只新建标注层。 |
| `bible/` | 机制工作区。当前只做**锚点记录先行**：`anchors/` 逐场锚点；跨锚候选综合暂不 active，早期候选已归档到 `archive/synthesis/`，后续锚点足够厚时再取回重审；最终才到 `policy.md` 人定稿机制。旧 Lore 等草稿已归档，不是 active prompt。 |
| `eval/` | 评测台：bare vs base 双臂消融协议 + 生成 prompt 脚手架。被测/判定走云 API 直调。fixtures = `tests/annotation/` 的 32 条 + 预登记判型。 |
| `canon/` | 正典只读快照（`maintext/卷01–11.json`，来自 units 分支）。机制冷启动来源；只读、不加工、不重建管线。 |
| `tools/` | 轻量辅助脚本；可读取只读底料生成临时视图或切片，但不得回写 `canon/` 或冻结探针。 |

新增任何目录前，先在本表声明它在"圣经 / prompt / eval / 产物"中的职责。

## 当前状态

架构当前口径见 `DESIGN.md`。纸面标注实验完成（`tests/annotation/`，DESIGN §7 step1）：环境压力×关系内压强双轴正交散开、trust 轴聚右端待 round3 补、相图只收窄目的族不决定接拒。机制工作区已改为锚点先行：`bible/anchors/` 已有卷01、卷02 两则锚点；早期候选已归档到 `bible/archive/synthesis/`；旧 `lore.md` 已归档。**下一步：补足关键锚点 → 再取回/重审候选 → 人定稿 Policy 端的墙 1–3 条机制（`bible/policy.md`）→ 同 commit 落 active prompt/eval 输入 → bare/base 首跑。**

## 承重纪律

1. 裸基线优先：圣经必须赢过裸模型才算真的加了东西。
2. 贴近正典只当警报，不当优化目标。
3. fit/validate 分离：round1/round2 是回归锚；holdout 须是新圣经 commit 后独立出题的 round3。
4. 机制写成可迁移的生成过程，标支持场景与复杂化反例，不停在标签层。
5. 圣经机制正文由人写；Claude 辅助论证与评测，不直接生成机制。
6. 被测走云 API 直调（上下文全可控），模型版本与采样参数记进 runs。
