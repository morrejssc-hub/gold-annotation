---
name: phase2-attribution
description: 为《狼与香辛料》语料做 Phase 2 说话人归属(uid→speaker 序列标注)。当用户要"跑 Phase 2""做归属/标说话人""给某章/全部章节标 speaker""phase2 提取"时使用。用 Codex subagent 并行扇出,每个 subagent 读整章+cast 产出 phase2/<篇名>.json。
---

# Phase 2 说话人归属 · 批量标注

归属标注的第二阶段：**每章一次**，整章正文 + `casts/<篇名>.json` 小角色表 + `dialogue.py` 抽出的带 uid 台词 → `phase2/<篇名>.json`（`uid → speaker`）。
前置：该篇必须已有 `casts/<篇名>.json`（Phase 1 产物）。范例产物见 `phase2/后日谈.json`，schema 见其 `schema_version`/`type_legend`。

**三条铁律（违反即重蹈 DESIGN-PIVOTS 的坑）：**
1. **整章塞进 context**，靠滚动在场状态 + 人设语癖 + 整章双向信息定夺。**绝不逐句 agent loop**——一个 subagent 一次读完整章、一次吐全章 `uid→speaker`。
2. **输出用 uid 键**，不 echo 原文，保留显式 abstain（`-`）。
3. cast 里的**视角相对称谓**（主人/旅伴/女子/太太）已按场景消解好——按 cast 的 `ambiguous`/`present_scope` 用，别静态映射。

> 一个 subagent 读整章 = 大进/小出，是设计许可的；被禁的是"逐句调用/ReAct 往回滚"。本 skill 的扇出粒度永远是**篇**，不是句。

## 执行步骤

工作目录基准：**仓库根目录**（`gold-annotation/`）。

1. **定范围**：从用户参数取章节（番外 `jsons/*.json`；正文 `maintext/卷NN.json` 按卷一张表）。
   - "全部/all" → 有 `casts/<篇>.json` 的全部；"剩余/补" → 有 cast 但 `phase2/` 还没产物的。
   - 默认**不覆盖**已存在的 `phase2/<篇名>.json`，除非用户说"重做/覆盖"。
   - 缺 `casts/<篇>.json` 的篇：先提示跑 Phase 1（cast-sheet skill），不要硬上。

2. **扇出**：每篇起一个 `general-purpose` subagent，用下方【SUBAGENT 提示词模板】（替换 `{SOURCE}`、`{CORPUS_DIR}`=`jsons` 或 `maintext`）。
   一次最多并行 ~6 个（同一条消息多个 Agent 调用），其余分批。大章节(>700 台词)正常，可单独成批。

3. **校验**（全部回来后，在 gold-annotation 下跑）：
   - `python3 phase2_eval.py phase2/<篇>.json`（或 `--all phase2`）：查①覆盖是否与 `dialogue.py` 完全对齐（无遗漏/多余/重复）②已核 gold 一致率③未核机器猜测的复核候选。
   - JSON 合法性：`python3 -c "import json;json.load(open('phase2/<篇>.json',encoding='utf-8'))"`。

4. **汇报**：每篇一行——台词数 / 覆盖✓ / gold 一致率 / abstain(`-`) 数 / med+low confidence 数 / 复核候选。**把 low/med confidence、abstain、与旧猜测冲突的复核候选单独列出请人定夺**（这是 gold 构建的人审环节）。

## SUBAGENT 提示词模板

```
你是《狼与香辛料》系列的说话人归属标注器。任务：为单篇章节产出 Phase 2【uid→speaker】JSON。
工作目录：仓库根目录（gold-annotation/）。这是 gold 数据，宁可标 abstain，不要硬猜。

步骤：
1. 读范例与 schema：phase2/后日谈.json（照其 labels 项结构、type_legend、字段）。
2. 读本篇角色表：casts/{SOURCE}.json —— 这是你的实体清单、视角相对称谓表、ambiguous 消解规则、倒指代回填线索、语癖签名。务必先吃透 focalizer_note / ambiguous / needs_registry。
3. 取章节文本：运行 `python3 render_chapter.py {CORPUS_DIR}/{SOURCE}.json`（**不要**再去 Read 整篇 JSON——那是缩进膨胀的冗余）。输出两块：
   [全文] 每句一行 `scene_sent│text`，是你做归属的完整上下文，**读完整章再下结论**（倒指代/晚点名要读到后文才能回填）；
   [待标台词] `uid \t 台词`，是你必须标的 uid 集合，不多不少。

归属规则：
- 维护滚动【在场集 + 上一说话人】：对白多为二人交替，靠紧邻叙述句的动作主语(“X说道/X反问/X笑了笑”)锚定，再用语癖(赫萝:汝/咱/呐/喔/呗)、知识域、关系称谓校验。
- canonical 一律用 cast 的 canonical 名（视角相对称谓如'主人/女子/太太'要归一到所指实体；按场景消解，见 cast.ambiguous 与 present_scope）。
- 倒指代回填：开头以泛称出现、后文才点名者，全部回填到该 canonical（cast.evidence.first_named 给了锚点）。
- 群戏/背景音/无法判定 → speaker 记 "-"（显式 abstain）。集体指代(那两人/老板们群口)若非单一说话人，也记 "-" 或 cast 里的集体实体，按 cast 处理。
- 区分四类 type：dialogue(正常台词) / vocalization(汪、哦、吼～、暗号等有主体的发声) / inner_monologue(焦点者内心独白被引号括起，speaker=思考者) / narration_quote(叙述引用的成语/比喻/旧话，非当下发言→speaker="-")。

输出：把结果写到 phase2/{SOURCE}.json（纯 JSON，UTF-8，结构同范例）：
  顶层含 schema_version="phase2-labels/0.1"、source、focalizer、cast_ref、method、present_state_notes、labels[]。
  labels 每项：{uid, speaker(canonical 或 "-"), type, confidence(high/med/low), basis(锚定依据，简短), note?(可选)}。
  uid 顺序与 dialogue.py 输出一致，覆盖其全部 uid。
最后用文字返回(不写文件)：①台词总数②abstain 数③你最不确定的 3-5 个 uid 及原因④双主角互换/群戏里最易错的轮替点。简洁即可。
```

## 注意

- subagent 出**候选**，人来定夺；low/med confidence 与 abstain 是给人审的信号，不是失败。
- 不改 `casts/*.json`、不改 `aliases.json`。Phase 2 只读 cast、只写 `phase2/`。
- 覆盖必须与 `dialogue.py` 严格对齐——`phase2_eval.py` 会卡这条；少一条多一条都要查。
- gold 一致率只以 `eval.tsv` 中 `checked=y` 的行为准；`checked` 为空的是机器猜测，冲突时以 phase2 整章判断为准并列为复核候选。
