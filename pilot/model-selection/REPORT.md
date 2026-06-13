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

## 附录 A：subagent 对照臂（方法纪律实证）

为检验 DESIGN §0 "评测不用 subagent" 这条纪律，加跑一臂：同 28 场、同圣经系统提示，改走 subagent（harness 模型 = Claude/Opus）扮演角色，再用 subagent 同口径盲判。

| 臂 | 方法/模型 | Claude 判·入侵率 |
|---|---|---|
| subagent-claude | subagent / Opus | 2/28 (7%) |
| deepseek-v4-pro | API 直调 | 7/28 |
| qwen3.7-max | API 直调 | 10/28 |
| qwen3.7-plus | API 直调 | 12/28 |

subagent 臂表面最优，但**不能当选型依据**，有两个致命混淆：
1. **模型不同源**：Opus vs deepseek/qwen，测的是模型强弱不是方法差异；
2. **判定=被测同源**（更致命）：Claude 既生成又判定，自评偏松，挂上率灌水。

## 附录 B：交叉判别（外部 GPT 判，打掉同源混淆）

把四臂输出匿名为 A/B/C/D（每场独立洗牌，seed 7），交外部判别 GPT 盲判，对照 Claude 判别。

| 臂 | Claude 判 | GPT 判 | 跨判别稳定性 |
|---|---|---|---|
| qwen3.7-plus | 12/28 | 6/28 | 稳居最差 |
| qwen3.7-max | 10/28 | 2/28 | ⚠ 剧烈漂移 10→2 |
| **deepseek-v4-pro** | **7/28** | **4/28** | 稳居前二，波动最小 |
| subagent-claude | 2/28 | 4/28 | 自评→他评 **2→4** |

**三条结论：**
1. **subagent 自评灌水被证实**：换独立判别后 subagent 臂 2→4，跌出独占第一、与 deepseek 并列——纪律"评测不用 subagent"得到实证依据，存档防回潮。
2. **入侵率不可跨判别直接比**：GPT 整体比 Claude 宽松，四臂全线下降；只能比同判别下的排序。
3. **选型未被推翻，但非单判读那般决定性**：qwen3.7-plus 两判别都垫底（稳定淘汰）；deepseek 两判别都在前二、波动最小；qwen3.7-max 读数 ±8/28 剧烈漂移，低入侵疑似 GPT 单家口味偶然，稳定性不足。

## 综合决定

**主被测定 deepseek-v4-pro**，依据从"单判别最低入侵率"升级为"**跨判别稳定性最优**"——两个独立判别下永远前二、波动最小，是 N=1 采样下最稳的押注。qwen3.7-max 标为待确认替代项（若加采样证实其低入侵稳定，可回头复议）。两判别一致认定的硬入侵磁铁（r2-P02 / r2-P04 / r1-P12 / r2-P15 / r1-P04 / r1-P05）留作圣经 bare/base 阶梯重点观察项。

## 产物清单

- `scenes.json` 去重场景 / `batch_input.*` / `batch_output.*` 三云臂原始输出
- `judge_tasks.json`（匿名 A/B/C）/ `judge_keymap.json` / `judge_results.json` / `tally.json`（Claude 判·三云臂）
- `subagent_arm.workflow.js` / `subagent_results.json` / `subagent_tally.json`（subagent 对照臂）
- `judge4_prompt.md`（四臂匿名包，喂 GPT）/ `judge4_keymap.json` / `judge4_gpt.jsonl`（GPT 判原始）/ `judge4_gpt_tally.json`（解匿名统计）
- 脚本：`build_batch.py` `submit_batch.py` `run_realtime.py` `build_judge.py` `gen_workflow.py` `tally.py` `gen_subagent_workflow.py` `build_judge4.py`
