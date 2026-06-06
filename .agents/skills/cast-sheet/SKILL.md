---
name: cast-sheet
description: 为《狼与香辛料》语料生成 Phase 1 角色表(cast sheet)。当用户要"建/补角色表""跑 cast""为某章/全部章节解析角色""Phase 1"时使用。用 Codex subagent 并行扇出,每个 subagent 读整章产出 casts/<篇名>.json。
---

# Phase 1 角色表 · 批量生成

归属标注的第一阶段：**每章一次**，整章正文 + focalizer → 一张角色表 `casts/<篇名>.json`。
解决倒指代回填、视角相对称谓(主人/旅伴/父亲)、泛称按场景消解、跨章点名。
规范与 schema 见 `PHASE1.md`，标准范例见 `casts/后日谈.json`。

**Codex 路线（本 skill）= subagent 扇出**；非 Codex 路线（百炼/Codex）用 `phase1_cast.py`。

## 执行步骤

工作目录基准：**仓库根目录**（本仓库即 `gold-annotation/`，章节正文在 `jsons/`）。

1. **定范围**：从用户参数取章节。
   - 语料分两套：**番外** = `jsons/*.json`（45 短篇，每篇一表）；**正文** = `maintext/卷NN.json`（11 卷，focalizer 全卷为罗伦斯，**按卷一张表**）。
   - 具体篇名/卷名（一个或多个）→ 就做这些。
   - "全部 / all" → 番外 `jsons/*.json` 全部（跳过坏 json：`幕间.json`）；正文 `maintext/*.json` 全部。
   - "剩余 / 补" → 列出语料目录里有、但 `casts/` 里还没有对应 `<篇名>.json` 的。
   - 默认**不覆盖**已存在的 `casts/<篇名>.json`，除非用户说"重做/覆盖"。

2. **取每篇 focalizer**：从 `focalizers.tsv` 的 `focalizer` 列按 `source` 查；查不到就让 subagent 自行从全文判断（第一人称"我"通常即视角）。

3. **扇出**：每篇起一个 `general-purpose` subagent，用下方【SUBAGENT 提示词模板】（替换 `{SOURCE}`/`{FOCALIZER}`）。
   一次最多并行 ~6 个（同一条消息里多个 Agent 调用）；其余分批。大章节(>1000句)正常，Codex 额度充足。

4. **校验**（全部回来后，在 gold-annotation 下跑）：
   - JSON 合法性：`for f in casts/*.json; do python3 -c "import json;json.load(open('$f',encoding='utf-8'))" && echo OK $f || echo BAD $f; done`
   - 若 `eval.tsv` 有这些章的已核 gold，跑覆盖检查（见 PHASE1.md / 历史会话里的覆盖脚本），确认 gold 标签都能在角色表里找到对应。

5. **汇报**：给用户一张表——每篇：实体数 / present 数 / ambiguous 数 / needs_registry 数 / subagent 自报的"最不确定处"。**把所有 `needs_registry`(★) 与 low/medium confidence 实体单独列出，请用户人工定夺**（这正是设计里"AI 列候选、人定夺"的环节）。

## SUBAGENT 提示词模板

```
你是《狼与香辛料》系列的角色解析器。任务：为单篇章节生成 Phase 1【角色表】JSON。
工作目录：仓库根目录（gold-annotation/）

步骤：
1. 读规范与范例（照其 schema 和规则）：PHASE1.md 与 casts/后日谈.json。
2. 读 canonical 专名种子：aliases.json。
3. 本篇 focalizer = {FOCALIZER}（若为空请自全文判断；第一人称"我"通常即视角，is_focalizer=true）。
4. 读**整篇/整卷**正文：番外为 jsons/{SOURCE}.json，正文为 maintext/{SOURCE}.json（doc.scenes[].sents[]，句号写作 sceneid_sentid；正文每个 scene 的 chapter 字段标原章）。读完再下结论。

关键规则（详见 PHASE1.md）：
- 倒指代必须回填：开头以泛称(女子/来客/少年/那男人/这女孩)出现、后文才点名的，把名字补到该实体，evidence 标 first_mention 与 first_named。
- focalizer 视角下的关系称谓(主人/旅伴/父亲/姐姐…)放进对应实体的 appellations，不要当独立实体；focalizer_note 写明各称谓指谁。
- 泛称若随场景指不同人，放进 ambiguous，写清按场景如何消解，不要塞进某实体 aka。
- 注意语癖签名(如赫萝:汝/咱/呐/喔)写进 speech 字段。
- 仅被提及、本篇无台词的角色 present=false，仍登记。
- 只能靠系列正典/主篇情节才能点名的(本章正文从不写出名字)，放进 needs_registry 标★，不要硬猜进 cast。
- 若发现**视角中途切换**(如尾声换人称)，在 focalizer_note 标明并在 ambiguous 记该段范围。
- canonical 尽量复用专名种子。

输出：把角色表写到 casts/{SOURCE}.json（纯 JSON，UTF-8，结构与范例一致）。
最后用文字返回（不写文件）：①每个实体一行 canonical+是否在场+关键 appellations/descriptors；②ambiguous 与 needs_registry 要点；③本篇最不确定的 1-2 处。简洁即可。
```

## 注意

- 这是 gold 构建的辅助：subagent 出**候选**，人来定夺，不要当成终稿。
- `casts/*.json` 是 Phase 2（uid→speaker 序列标注）的输入。
- 不改 `aliases.json`（全局只放专名）；关系称谓只活在各章 cast 的 `appellations` 里。
