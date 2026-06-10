# 角色扮演 gold 构建（《狼与香辛料》语料）

**终点：在场景下模仿角色回应（角色扮演）的 SFT gold 数据。回应 = 动作 + 台词。**
说话人归属（speaker attribution）**不是终任务，是切角色数据的底料**——判断每句话归谁，才能机械组装 (场景上文 → 该角色回应) 成对样本。详见 [`UNITS.md`](UNITS.md)。正文 11 卷的作业规程（精度优先 / proposer–verifier / 番外预演实证）见 [`正文-SOP.md`](正文-SOP.md)。

> 这套方案**转向过两次 + 一次目标归位**。动手改架构前，先读 [`DESIGN-PIVOTS.md`](DESIGN-PIVOTS.md)——
> 尤其「第 4 节·反复踩的坑」。旧归属两阶段之前的代码全在 [`archive/`](archive/)。

## 当前架构（自下而上：素材 → 底料 → 角色单元 → 样本）

```
Phase 0  视角判定     focalizers.tsv（手填 POV）
Phase 1  角色表       整章 → AI 列候选角色表 + 标判不准项 → 人定夺（非 agent）
                      产物 casts/<篇>.json：每章 {专名/别名/关系称谓 → canonical, 语癖签名}；含倒指代回填
Phase 2  归属(底料)   整章 → uid→speaker（id 键、保留显式 abstain）
Units    角色单元     整章 → 每句 involves:[{char, role∈说/做, conf}]；双模型(Opus×codex)交叉验证
                      → 人工 audit(分歧)/抽检(共谋盲区) → units_merge → gold
组装     机械抽取     src/units_assemble.py：按 uid 序抽某角色的回合，渲染 (场景上文→回合) 样本（无 AI）
```

三条不能违反的约束（详见 DESIGN-PIVOTS / CLAUDE.md）：①归属是**带状态的篇章级序列标注**，不是单条 i.i.d. 分类；②关系称谓（主人/旅伴/父亲）**视角相对，只进各章 cast 的 appellations，绝不进全局 `aliases.json`**；③**不用 agent、不逐句循环**——整章塞进 context，输出用 uid 键、保留显式 abstain（`-`）。

## 文件（土台 + gold + 数据）

| 文件 | 角色 |
|---|---|
| `jsons/<篇名>.json` | **番外素材**（45 篇短篇，`scenes[].sents[]`）。坏档 `幕间.json` 跳过。 |
| `maintext/卷NN.json` | **正文素材**（11 卷，共 87 章 46,534 句，uid 全卷唯一）。focalizer 全卷为罗伦斯，**按卷一张角色表**。 |
| `aliases.json` | 全局**专名**别名表（不放代词/关系称谓）。Phase 1 角色表的种子。 |
| `casts/<篇名>.json` | **Phase 1 产物**：每章一张角色表（44/44 已生成、人工核验）。下游输入。 |
| `registry_review.tsv` | needs_registry 人工裁决总账（58 条），已回写各 cast，仅作审计留存。 |
| `phase2/<篇名>.json` | **Phase 2 产物**：每章 `uid→speaker`（schema=`phase2-labels/0.1`）。units 说层回归基线。 |
| `units/<model>/<篇名>.json` | **Units 产物**：每句 `involves:[{char,role∈说/做,conf}]`（schema=`units/0.2`）。`<model>`=claude/gpt 双跑互证。 |
| `units/audit_<篇>_v2.tsv` | 双模型**分歧**人工裁决（含 audit 列 A/B/角色名）。 |
| `units/fix_<篇>.tsv` | 抽检发现的**共谋盲区**人工修正通道。 |
| `units/gold/<篇名>.json` | **合并 gold**（一致取共识 + audit 裁决 + fix 覆盖）。 |
| `focalizers.tsv` | Phase 0：每篇视角角色（手填；Phase 1 已校正 10 行）。 |
| `eval.tsv` | 人工 gold（86 行）：`checked=y` 才是真 gold，空 checked 是未核机器猜测。 |
| `sheet.tsv` | Pivot 0 累积人工 gold（gold_speaker 可复用）。 |

工具脚本：

| 脚本 | 作用 |
|---|---|
| `src/dialogue.py` | 纯机械抽台词 + 确定性 uid + 上下文窗口。`--all jsons\|maintext` 全量。 |
| `src/phase1_cast.py` | Phase 1：整章 → 角色表提示词/API 调用（`--backend dump\|claude\|bailian\|codex`）。 |
| `src/normalize_casts.py` / `src/finalize_registry.py` | 跨卷音译归一 / registry 裁决回写各 cast。 |
| `src/render_chapter.py` | **Phase 2/Units 紧凑输入**：整章渲染成「全文(scene_sent 标号, 含 `[在场]`) + 待标 uid」单份文本。 |
| `src/phase2_eval.py` | Phase 2 校验：覆盖对齐 + 已核 gold 一致率 + 复核候选。 |
| `src/units_check.py` | Units 自检：覆盖、role/char 域、说≤1/句、有引号≠说审计、说层 vs `phase2/` 回归（顺手白捡，非主柱）。 |
| `src/units_diff.py` | 两模型 units `(uid,char,role)` 三元组分歧分桶 → `audit_<篇>.tsv`。 |
| `src/units_sample.py` | **抽检单生成器**（零模型，从两臂一致句采难桶 多引号/群戏/互换/焦点低）。质检主柱。 |
| `src/units_merge.py` | 机械合并双模型 → gold：一致取共识(conf 取低档) + audit 裁决 + fix 覆盖。 |
| `src/units_assemble.py` | 按 uid 序抽某角色回合、渲染角色扮演样本（target 侧默认滤 conf=low 做）。**无 AI**。 |

skills（`.claude/skills/`）：`cast-sheet`(Phase 1 扇出)、`phase2-attribution`(Phase 2 扇出)、`units-extract`(Units 抽取，A 臂 subagent + B 臂 codex 同享此 prompt)。

## 进展（baseline）

- **Phase 1 完成**：`casts/` 覆盖全部 44 章，JSON 合法、人工核验；focalizer 校正 10 篇、跨卷音译归一、needs_registry 58 条全核。每份 cast 自足。
- **Phase 2 落地**：流程跑通 + 工具链（skill / `src/render_chapter.py` / `src/phase2_eval.py`）；已产 `phase2/` 三篇，覆盖与 `src/dialogue.py` 对齐、已核 gold 100%。
- **Units 层脚手架基本可用**：终点归位为角色扮演；按句 `说/做` 多标签 + 双模型（Opus×codex/GPT-5.5）交叉验证 + 抽检主柱。判据固化两条新规（**现场性闸**：辖域判据非词表；**心理活动走显式施事测试**：需显式心理动词+本人施事，裸命题→`[]`）。
  - **merged gold 两篇**：旅途余白、后日谈（后日谈 448 句，校验 OK，说层 vs Phase2 98%）。
  - 将晓之色、麦穗：已有双臂产物 + audit/sample，待人审 → merge。

## 下一步：扇出（fan-out）

脚手架到基线，铺开番外 45 篇 + 正文 11 卷。单篇全链命令：

```bash
python3 src/render_chapter.py jsons/<篇名>.json                       # 抽取输入（双模型同享；含 [在场]）
# A 臂 Claude subagent（units-extract skill）+ B 臂 codex 同 prompt 各产一份
python3 src/units_check.py units/claude/<篇>.json                     # 单份自检 + 说层回归
python3 src/units_diff.py units/claude/<篇>.json units/gpt/<篇>.json  # 分歧 → audit_<篇>.tsv
python3 src/units_sample.py <篇>                                       # 抽检单（人审主柱）
#   人工填 audit_<篇>_v2.tsv（A/B/角色名）+ fix_<篇>.tsv（共谋盲区）
python3 src/units_merge.py <篇>                                        # → units/gold/<篇>.json
python3 src/units_assemble.py units/gold/<篇>.json --char 赫萝 --samples 2  # 机械组装样本
```
