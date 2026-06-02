# 归属 gold 构建（当前方向：章节级序列标注）

任务：**给定小说正文，判断每条台词的说话人**，为 SFT 产出可靠的训练/评测数据。

> 这套方案**已转向两次**。动手改之前，请先读 [`DESIGN-PIVOTS.md`](DESIGN-PIVOTS.md)——
> 尤其是「第 4 节·反复踩的坑」，避免重蹈覆辙。旧两阶段的代码全在 [`archive/`](archive/)。

## 当前架构（Pivot 2，两阶段·无 agent）

```
Phase 0  视角判定     focalizers.tsv（已有，手填 POV）
Phase 1  角色表解析   整章 → AI 列候选角色表 + 标判不准项 → 人定夺（辅助工具，非 agent）
                      产物：每章 (focalizer) → {专名/别名/关系称谓 → canonical, 一行语癖签名}；含倒指代回填
Phase 2  序列标注     每窗 = 角色表(小) + 带 uid 台词 + 滚动状态 → uid→speaker（窗口化、id 键、可续）
```

要点（详见 DESIGN-PIVOTS）：归属是**带状态的篇章级问题**，不是单条 i.i.d. 分类；
关系称谓（主人/旅伴/父亲）按章按 focalizer 解析、不进全局别名表；
整章能塞进 context，**不用 agent**；输出用 uid 键、窗口化以绕开"大进大出"。

## 文件（保留 = 土台 + gold + 数据）

| 文件 | 角色 |
|---|---|
| `jsons/<篇名>.json` | **番外素材**（45 篇短篇，`scenes[].sents[]`）。Phase 1/dialogue 的输入；坏档 `幕间.json` 跳过。 |
| `maintext/卷NN.json` | **正文素材**（11 卷，由 `sw-sft/main_text.json` 按卷切分；章→scenes 扁平、scene id 全局重编、原章标题存于 `scenes[].chapter`）。共 87 章 46,534 句，uid 全卷唯一。focalizer 全卷为罗伦斯，故按卷一张角色表。`python3 dialogue.py --all maintext` 抽全量。 |
| `aliases.json` | 全局**专名**别名表（不放代词/关系称谓）。Phase 1 角色表的种子。已含跨卷音译变体归一与 `_note_艾普`。 |
| `casts/<篇名>.json` | **Phase 1 产物**：每章一张角色表（44/44 已生成、人工核验）。Phase 2 输入。 |
| `registry_review.tsv` | needs_registry 人工裁决总账（58 条，verdict=drop/keep_local/resolve）。已回写进各 cast，仅作审计留存。 |
| `normalize_casts.py` | 跨卷音译归一脚本（canonical 取官方名、变体进 aka）。 |
| `finalize_registry.py` | 把 `registry_review.tsv` 裁决回写各 cast 的 needs_registry，使每份 cast 自足。 |
| `dialogue.py` | 纯机械抽取：台词 + 确定性 uid + 上下文窗口（独立可跑）。 |
| `render_chapter.py` | **Phase 2 / Units 紧凑视图**：整章渲染成「全文(scene_sent 标号) + 待标 uid 列表」单份文本，替代「Read 整篇 JSON + dialogue.py 带窗口输出」的冗余（输入字节 ~−75%）。uid 逻辑复用 `dialogue.py`。 |
| `phase2/<篇名>.json` | **Phase 2 产物**：每章 `uid→speaker`（`labels[]`：speaker/type/confidence/basis）。schema=`phase2-labels/0.1`，范例 `phase2/后日谈.json`。 |
| `phase2_eval.py` | Phase 2 校验：①覆盖与 `dialogue.py` 严格对齐 ②对 `eval.tsv` 已核 gold(checked=y) 算一致率（经 cast 别名归一）③未核机器猜测的复核候选。 |
| `dialogue_all.tsv` | 全量已抽台词（`python3 dialogue.py --all jsons`）。 |
| `focalizers.tsv` | Phase 0：每篇视角角色（手填；Phase 1 已校正 10 行，note 标 `[Phase1校正]`）。 |
| `eval.tsv` | 人工 gold（86 行已核）：验证集 + 本次转向的证据。**注意**：`checked=y` 才是真 gold；`checked` 为空的行是未核机器猜测（gold==guess），不计入一致率。 |
| `sheet.tsv` | Pivot 0 累积人工 gold（gold_speaker 可复用）。 |
| `.claude/skills/phase2-attribution/` | Phase 2 的 subagent 扇出流程（一个 subagent 一篇，读整章+cast 一次产出）。 |
| [`UNITS.md`](UNITS.md) | **角色单元层规范**：终点=角色扮演、单元=按句 `说/做` 多标签、双模型交叉验证、机械组装。Phase 2 的泛化与延伸。 |
| `units/<model>/<篇名>.json` | **Units 产物**：每句 `involves:[{char,role∈说/做,conf}]`（schema=`units/0.2`）。`<model>`=claude/gpt 双跑互证。 |
| `units_check.py` | Units 自检：覆盖、role/char 域、说≤1/句、有引号≠说审计、说层 vs `phase2/` 回归。 |
| `units_diff.py` | 两模型 units 的 `(uid,char,role)` 三元组分歧分桶 → 审计清单。 |
| `units_assemble.py` | 按 uid 序机械抽某角色流/回合、渲染 (场景上文→回合) 角色扮演样本。**无 AI**。 |
| `units_prompt_<篇>.txt` | Units 抽取提示词（A/B 双模型逐字相同）。 |

## 进展

- **Phase 1 完成**：`casts/` 覆盖全部 44 章（坏档 `幕间.json` 跳过），JSON 全部合法、已人工核验。详见 [`PHASE1.md`](PHASE1.md) 的「进展」。
- focalizer 校正 10 篇、跨卷音译归一、needs_registry 58 条全部人工 check。每份 cast 自足（无需外部总账即可进 Phase 2）。
- **Phase 2 起步**：流程跑通并落地工具链——`phase2-attribution` skill（subagent 扇出）、`render_chapter.py`（紧凑输入）、`phase2_eval.py`（覆盖+一致率校验）。已产出 `phase2/后日谈.json`、`phase2/旅途余白.json`，覆盖均与 `dialogue.py` 完全对齐、已核 gold 100%，并各纠正 1 处 `eval.tsv` 未核猜测（后日谈 5_12、旅途余白 3_23）。
- **目标归位 + Units 层试点**（详见 [`UNITS.md`](UNITS.md)）：终点确认为**角色扮演**（归属是切数据的底料）；落地按句 `说/做` 多标签 units、双模型（Opus×codex/GPT-5.5）交叉验证。**旅途余白** 试点全链跑通：收紧 schema 后两模型一致率 **76%→96%**，并用 `units_assemble.py` 机械组出赫萝/罗伦斯角色流。

## 下一步

进入 **Units 层**（[`UNITS.md`](UNITS.md) 第 9 节）：人工固化旅途余白 units gold → 定稿角色扮演 jsonl 格式 → 沉淀 `units-extract` skill → 铺开番外/正文卷。命令：

```bash
python3 render_chapter.py jsons/<篇名>.json                 # 抽取输入（双模型同享）
python3 units_check.py units/<model>/<篇名>.json            # 单份自检 + 说层回归
python3 units_diff.py units/claude/<篇>.json units/gpt/<篇>.json   # 跨模型分歧 → 审计
python3 units_assemble.py units/claude/<篇>.json --char 赫萝 --samples 2  # 机械组装
```
