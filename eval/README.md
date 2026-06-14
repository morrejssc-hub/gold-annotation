# 评测台

bare vs base 双臂消融，验 Policy 端的墙圣经是否真有贡献。架构见 `DESIGN.md` §0.1、§6。

| 文件 | 用途 |
|---|---|
| `protocol.md` | 评测协议：双臂、被测/判定 API 直调、ground truth、通过线、runs 记录、fit/validate。 |
| `prompt.md` | 生成 prompt 脚手架：system(圣经组装) + 情景 fixture 输入契约 + 判定输出契约。 |
| `runs/` | 跑批结果（模型版本/采样参数/圣经 commit 全记，缺则回归不可比）。待首跑后建。 |

**fixtures** = `tests/annotation/round1-2-annotation.md` 的 32 条（场景五元组 + 补充背景 + 目的 + 手段 + 预登记判型）。机器可读 JSONL builder 待 Policy 正文落地后建——无圣经正文跑不了 base 臂。

## 纪律

- 被测、判定均走**云 API 直调**，不用 subagent（纪律7：harness 提示词污染上下文；REPORT 附录 A/B 已实证灌水）。
- 判定模型可与被测异家族，降低"判定=被测同源"灌水。
- round1/round2 = 回归锚；全强度证伪 = round3 holdout（DESIGN §8 覆盖要求）。
