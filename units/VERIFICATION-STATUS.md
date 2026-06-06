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

## 已知问题 / 待办
- `units_diff.py` 输出文件名 bug：审计 tsv 文件名未按当前篇取，曾把白色道路 diff 误写成 `audit_旅途余白.tsv`（已从 HEAD 恢复）。**修脚本前，跑 diff 后务必核对输出文件名。**
- sonnet 下位替代弱点：偶把拟声"哇啊/呵"误标成"说"；偶把全角引号写成半角破坏 JSON（`units_check` 的 json.load 会卡住，用 render 原文重建该行 text 即可修）。
- 提速路径：`units_api.py` 单轮 API 抽取脚本已就绪（比 subagent 快一个数量级），待选可用 API 端点（anyrouter 推理端当时 503/429 不可用）。
