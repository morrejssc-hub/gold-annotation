# units 校验状态（截至 2026-06-06）

每篇角色单元产物的**校验等级**。重点是回答：**哪些还没经过"好模型"（opus / gpt-5.5 high）交叉或审计，不能当 gold**。
此文件为人工快照，磁盘为准；新增产物后据 `units_check.py` / `units_diff.py` / 强模型质检结果更新本表。

## 图例

- **臂**：`opus`=units/claude（Claude A 臂）｜`sonnet`=units/sonnet（sonnet-4.5 下位替代试验）｜`gpt`=units/gpt（B 臂，gpt-5.4-mini high 抽取）
- 校验等级：
  - **L3 gold**：已固化 `units/gold/`。
  - **L2 强校验**：经强模型交叉/审计——有 `audit_<篇>.tsv`（opus×gpt diff）**或** gpt-5.5 high 只读质检报告。可作 gold 候选。
  - **L1 仅结构**：`units_check.py` OK，但**未经任何强模型交叉**。**不可当 gold。**
    - **L1a 双臂齐备·待 diff**：两份不同家族产物已在，跑一次 `units_diff` 即可升 L2。
    - **L1b 单臂·无对照**：只有一份产物，需补另一臂或强模型审计。
  - **L0 未开始**：尚无任何 units 产物。

---

## L3 gold（2）
后日谈 · 旅途余白

## L2 强校验，可作 gold 候选（9）
| 篇 | 依据 |
|---|---|
| 嫩绿色的小径 | audit（opus×gpt） |
| 狼与另一个生日 | audit |
| 狼与将晓之色 | audit |
| 狼与彩虹色的音乐 | audit |
| 狼与硕果之夏 | audit |
| 狼与金黄色的麦穗 | audit |
| 狼与银色的叹息 | audit |
| 羊皮纸与涂鸦 | audit |
| 狼与轻咬的牙 | gpt-5.5 high 质检（`tmp/fanout-logs/validate_狼与轻咬的牙_gpt55_high.md`）+ 已定点修正 |

## ⚠️ L1a 双臂齐备，**未做 diff**（7）—— 跑一次 `units_diff` 即可升级
| 篇 | 已有臂 |
|---|---|
| 狼与白色的道路 | opus + sonnet + gpt |
| 狼与春天落下的东西 | opus + gpt |
| 狼与白色的猎犬 | sonnet + gpt |
| 狼与红霞色的礼物 | sonnet + gpt |
| 狼与羊毛刷 | sonnet + gpt |
| 狼与青草色的小路 | sonnet + gpt |
| 狼与饴糖色的日常 | sonnet + gpt |

## ⚠️ L1b 单臂，**无任何对照**（11）—— 需补另一臂或强模型审计
| 篇 | 仅有臂 |
|---|---|
| 两匹狼的婚礼 | opus |
| 少年、少女与白花 | opus |
| 旅行商人与黯色的骑士 | opus |
| 牧羊人与黑骑士 | opus |
| 狼与一身泥的送行狼 | opus |
| 狼与宝石之海 | opus |
| 狼与尾巴的圆舞 | opus |
| 狼与收获之秋 | opus |
| 狼与旅行之卵 | opus |
| 狼与星空下的远吠 | opus |
| 狼与灰色的笑颜 | gpt |

## L0 完全未开始
**番外（15）**：狼与昔日猎犬的叹息 · 狼与森林色彩 · 狼与橡实面包 · 狼与泉烟彼方 · 狼与琥珀色的忧郁 · 狼与秋色笑容 · 狼与花瓣香 · 狼与蓝色的梦 · 狼与蜜渍桃子 · 狼与辛香料的回忆 · 狼与金黄色的约定 · 狼与黄金色的约定 · 苹果的红、天空的蓝 · 金黄色的记忆 · 黑狼的摇篮

**正文卷（11）**：卷01–卷11（每卷 3000–8000 句，体量大）

---

## units/qwen —— 全番外统一臂（2026-06-06，qwen3.7-max batch 单轮）
**44 篇番外全部覆盖完整**（百炼 batch 50% 成本 112 请求 + 同步补漏）。说话人 vs opus 仅差 1 句、vs sonnet 0 句 → 作 **gold 主力候选臂**。
- char 越界已机械修（橡实 艾莉莎→艾尔莎 81 处）。
- **双说 10 句待人工降级**（多为合法双人同句，规范欠定）：两匹狼婚礼 2_706/2_772、少年少女 14_14、尾巴圆舞 3_73、橡实 4_381、泉烟彼方 7_87、灰色笑颜 7_9、金黄记忆 11_19/11_61、黑狼摇篮 20_30。
- 下一步：qwen × opus/gpt 互证（`units_diff` → audit → `units/gold/`）；正文 11 卷 `--scope vols` 同法 batch。

## 已知问题 / 待办
- ~~`units_diff.py` 输出文件名 bug~~ **已修**：`--tsv` default 改为按 a 的 source 自动命名（`units/audit_<source>.tsv`）。
- LLM 抽取共性弱点（已在 `units_api.parse_units` repair 兜底）：偶把拟声误标"说"、偶把全角引号写半角、偶发多余 `]`/双说；坏行用 render 原文回填 text。
- ~~提速路径待选端点~~ **已落地**：百炼 qwen3.7-max batch（50% 成本）。关键三招：`--no-thinking`（治推理模型偷懒/中断）、always `only_uids`（治单段跳采样）、自动分段（治大章输出撞顶）。anyrouter 推理端不可用已弃。
