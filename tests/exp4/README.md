# exp4 保留测试包

这个目录是从旧 `experiments/exp4-core-function/` 拆出的最小保留集。

## 内容

| 文件 | 用途 |
|---|---|
| `round1.frozen.md` | round1 目的合法性探针冻结题，14 条。 |
| `round2.frozen.md` | round2 目的合法性探针冻结题，18 条。 |
| `SPEC.md` | 探针出题规范。 |
| `bareR-protocol.md` | 全量 v3 vs 裸 R 的双臂协议。 |
| `paper-check.md` | v3 纸面体检记录。 |
| `runtime.full.eval.md` | exp4 v3.1 全量 eval runtime 投影，用作旧架构对比。 |
| `runtime.bareR.eval.md` | exp4 v3.1 裸 R eval runtime 投影，用作旧架构对比。 |
| `VERIFICATION.md` | exp4 实证状态总账。 |
| `runs/round1.md` | round1 原始运行结果。 |
| `runs/round1-regression.md` | round1 回归运行结果。 |
| `runs/round1-bareR.md` | round1 全量 v3 vs 裸 R 运行结果。 |

## 使用方式

这些文件不是新系统的历史负担，只承担两件事：

1. 作为新圣经/新 prompt 的压力测试题库。
2. 作为旧 exp4 结果的对照基线，防止“新架构更干净但行为退化”。

如果后续要正式跑 round2，请把被测材料指向 `rp/` 当前圣经与 prompt，并把新结果写入新的 `runs/` 文件，不要改写冻结题。

