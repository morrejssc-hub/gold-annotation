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

## 旧路径映射表（失联引用对照）

本目录文件自旧分支 `feat/bible-decision-loop@a784774` 的 `experiments/exp4-core-function/` 拍平搬入（11 对文件逐一 `git diff` 验证零漂移）。**冻结文件正文中的内部引用仍指向旧结构，一律按下表换算，不改写冻结正文**：

| 冻结正文中的旧引用 | 本目录实际位置 |
|---|---|
| `probes/probes.frozen.md` | `round1.frozen.md` |
| `probes/round2.frozen.md` | `round2.frozen.md` |
| `probes/SPEC.md`、`probes/bareR-protocol.md`、`probes/paper-check.md` | 同名文件在本目录根 |
| `probes/runs/*` | `runs/*` |
| `runtime.eval.md`、`../runtime.eval.md` | `runtime.full.eval.md` |
| `runtime.bareR.eval.md` | 同名，在本目录根 |
| `atlas/`、`atlas-bareR/`、`compile.py`、`PLAN.md`、`arms/`、`probes/blind/` | **不在本分支**——runtime 两份投影是只读冻结快照（文件头"勿手改——改 atlas/"的指令在本分支无效，本分支一律不改）；需要源卡时去旧分支 `feat/bible-decision-loop` 取 |

## 使用方式

这些文件不是新系统的历史负担，只承担两件事：

1. 作为新圣经/新 prompt 的压力测试题库。
2. 作为旧 exp4 结果的对照基线，防止“新架构更干净但行为退化”。

如果后续要正式跑 round2，请把被测材料指向 `rp/` 当前圣经与 prompt，并把新结果写入新的 `runs/` 文件，不要改写冻结题。

