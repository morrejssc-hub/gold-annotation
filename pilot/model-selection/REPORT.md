# 被测模型选型 pilot · 判定报告

> 2026-06-13 跑完定稿。本目录就此冻结。判定者 = Claude（盲判，逐场景一 subagent，不知模型身份）。

## 结论

**主被测选 deepseek-v4-pro。** 三项指标同向领先，不构成打平。

| 模型 | 文学先验入侵率 | runtime 执行失败 | 文笔均分 | 目的挂根（挂上/勉强/挂不上） |
|---|---|---|---|---|
| **deepseek-v4-pro** | **7/28 (25%)** | **2** | **4.14** | **18 / 8 / 2** |
| qwen3.7-max | 10/28 (36%) | 5 | 3.79 | 11 / 13 / 4 |
| qwen3.7-plus | 12/28 (43%) | 3 | 3.75 | 13 / 11 / 4 |

- 主指标入侵率：deepseek 比次低的 qwen3.7-max 低 3/28。协议规定"差距**小于** 3/28 视为打平"——恰为 3，不打平。
- 即便按打平阈值放宽，deepseek 在 runtime 失败（2 vs 5 vs 3）、文笔（4.14 vs 3.79/3.75）、挂根率（18/28 vs 11/13）三项副指标上同向最优，裁决无歧义。

## 入侵偏置分布

| 模型 | 戏剧化升级 | 意义背书 | 自我解释 | 和解收尾 |
|---|---|---|---|---|
| deepseek-v4-pro | 3 | **1** | 3 | 0 |
| qwen3.7-max | 3 | 4 | 3 | 0 |
| qwen3.7-plus | 5 | 4 | 2 | 1 |

关键差异在**意义背书**型（把平静日常拔成"确认关系意义/读心"的目的）：deepseek 只栽 1 次，两个 qwen 各栽 4 次。这正是关系第一公民架构最要纠偏的入侵类型——平场里编出关系试探/丧失焦虑。deepseek 的残余入侵更多是"自我解释"（目的层把依恋写成显性动机），偏 runtime 提示工程可压，不是先验顽固。

## 共同难点场景（先验磁铁）

- **r2-P17**（例行拒签 → 读心）：三臂全栽，都把"伴侣拒签"读成"确认是否出于珍视"的关系意义确认。最强的平场入侵诱饵。
- **r1-P11 / r2-P15**：多臂栽在"目的层直球暴露依恋/丧失危机框"。
- 这几条留作 bare/base 阶梯的重点观察项：圣经若有效，应当在这些场景上把入侵压下去。

## 限度（诚实声明）

- 单采样 N=1，读数有方差；上表差距已计入 3/28 打平阈值判读。
- 场景出自圣经作者读过的 exp4 冻结集，测的是**模型先验差异**，不是圣经效力（那是之后 bare/base 阶梯的事）。
- 判定者与候选之一（无）非同家族，但与圣经辅助论证者同源；逐条理由存于 `judge_results.json` 供人复核。

## 模型版本回执

百炼实查可用 ID（`submit_batch.py check`，2026-06-13）：
- qwen3.7-plus → 快照 `qwen3.7-plus-2026-05-26`（Batch 接口）
- qwen3.7-max → 快照 `qwen3.7-max-2026-06-08`（Batch 接口）
- deepseek-v4-pro → 无快照 ID，Batch 白名单不含 v4，走实时接口（偏差：去 seed，详见 PROTOCOL §限度）
- 参数统一：temperature 0.7 / top_p 0.9 / max_tokens 500 / seed 7（deepseek 实时去 seed）/ enable_thinking=false

## 产物清单

- `scenes.json` 去重场景 / `batch_input.*` / `batch_output.*` 三臂原始输出
- `judge_tasks.json`（匿名 A/B/C）/ `judge_keymap.json`（解匿名）
- `judge_results.json` 逐场景盲判 / `tally.json` 解匿名统计
- `judge.workflow.js` 盲判 workflow / `gen_workflow.py` `tally.py` `build_judge.py` 脚本
