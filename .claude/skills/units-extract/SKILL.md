---
name: units-extract
description: 为《狼与香辛料》语料抽取角色单元层(按句 说/做 多标签，双模型互证 → gold)。当用户要"跑 units""抽角色单元""做说/做标注""units 提取""给某章/全部章节抽 units"时使用。用 Claude subagent 并行扇出抽 claude 一臂，再配第二模型(codex/GPT)同 prompt 跑一遍，diff→audit→merge 成 gold。
---

# 角色单元层抽取 · 双模型互证

角色扮演 SFT 的底料：**每章一次**，整章正文(含 `[在场]`) + `casts/<篇名>.json` → `units/<model>/<篇名>.json`——给**全章每一句**标 `involves:[{char, 说/做, conf}]`。
终点是"在场景下模仿角色回应(动作+台词)"，units 是唯一要抽的最底层。详见 [`UNITS.md`](../../../UNITS.md)。范例产物 `units/gold/旅途余白.json`、`units/claude/旅途余白.json`，schema=`units/0.2`。

前置：该篇必须已有 `casts/<篇名>.json`（Phase 1 产物）。缺则先跑 cast-sheet skill，别硬上。

**三条铁律（违反即重蹈 DESIGN-PIVOTS 的坑）：**
1. **整章塞进 context**，一个 subagent 一次读完整章、一次吐全章 units。**绝不逐句 agent loop**。扇出粒度永远是**篇**。
2. **输出按句、用 uid 键**，逐字原文 verbatim，纯写景句 `involves:[]`（显式弃标，不强归焦点者）。
3. **护栏（越线即废）**：单元只记 `who + 说/做 + 原文`。**绝不**写动作类型/动机/对谁/因果/情绪。

> **双模型是本层的命脉**：两个**不同家族、势均力敌**的模型(Opus 4.8 × codex/GPT-5.5)各跑一遍**同一份 prompt**，分歧即审计信号(`units_diff`)。弱模型/同模型重采样无意义。但**跨模型一致只抓"分歧"，抓不到"两家共错"的共谋盲区**——共谋盲区靠 `units_check` 抽检预筛 + 人工抽检 + `fix` 通道兜底（见 UNITS.md §5）。

## 执行步骤

工作目录基准：**仓库根目录**（`gold-annotation/`）。

1. **定范围**：从用户参数取章节（番外 `jsons/*.json`；正文 `maintext/卷NN.json` 按卷一张表）。
   - "全部/all" → 有 `casts/<篇>.json` 的全部；"剩余/补" → 有 cast 但 `units/claude/` 还没产物的。
   - 默认**不覆盖**已存在产物，除非用户说"重做/覆盖"。

2. **A 臂(claude)扇出**：每篇起一个 `general-purpose` subagent，用下方【SUBAGENT 提示词模板】，`{OUTDIR}`=`units/claude`、`{MODEL}`=`opus-4.8`。一次最多并行 ~6 个（同消息多 Agent 调用），其余分批。

3. **B 臂(第二模型)**：**同一份 prompt** 用 codex 跑一遍，写 `units/gpt/<篇>.json`、`{MODEL}`=`gpt-5.5`。
   - **codex CLI**（`/root/.local/bin/codex`，ChatGPT 登录态、openai 默认模型，与 Opus 不同家族）。把 SUBAGENT 模板填好(`{OUTDIR}`=`units/gpt`)写入临时文件，非交互跑：
     ```bash
     export PATH="$HOME/.local/bin:$PATH"
     timeout 900 codex exec --sandbox workspace-write --skip-git-repo-check \
       -C /root/gold-annotation - < /tmp/units_b_<篇>.txt
     ```
     `--sandbox workspace-write` 让它能跑 `render_chapter.py` 并写 `units/gpt/`。它是 agent，会自己读 cast/render、自检、落盘；单篇约 6–13 万 tokens、数分钟。多篇可后台并行。
   - 备选 API 后端（`OPENAI_API_KEY` / `DASHSCOPE_API_KEY`，OpenAI 兼容）。无第二模型时**只出 A 臂 + 结构自检**，并明确告知"缺互证、未出 gold"。
   > 实测(将晓之色)：codex 79/79 覆盖、`units_check` OK、与 A 臂三元组一致 87%、**说话人分歧 0**、9 句涉及角色分歧入 audit。codex 还自发把「有引号≠说」判对(1_38 归做)，与 A 臂分歧恰好落在规范欠定处——双家族互证如期生效。

4. **校验 + 互证 + 固化**（产物回来后，在 gold-annotation 下跑）：
   ```bash
   python3 src/units_check.py units/claude/<篇>.json      # 结构不变量 + 抽检预筛(同句多引号) + (顺手)说层回归
   python3 src/units_check.py units/gpt/<篇>.json
   python3 src/units_diff.py units/claude/<篇>.json units/gpt/<篇>.json --tsv units/audit_<篇>.tsv
   # 人工填 audit 列(A/B/点名角色) → 另存 units/audit_<篇>_v2.tsv
   # 共谋盲区(抽检预筛 ⚑ + 难桶随机样发现的两家共错) → units/fix_<篇>.tsv
   python3 src/units_merge.py <篇>                          # 一致取共识 + audit 裁决 + fix 覆盖 → units/gold/<篇>.json
   python3 src/units_check.py units/gold/<篇>.json
   ```

5. **汇报**：每篇一行——句数 / 覆盖✓ / 说句数 / `[]`空句数 / 两模型三元组一致率 / 分歧句数 / **抽检预筛 ⚑ 句**。**把分歧集、low/med-conf、抽检预筛句单独列出请人定夺**（audit 管两模型分歧、fix 管两模型共错，都是 gold 构建的人审环节，不是失败）。

## SUBAGENT 提示词模板

```
你是《狼与香辛料》系列的"角色单元"抽取器。本语料用于"在场景下模仿角色回应"的 SFT，
要把每句话归到"哪个角色 说了 / 做了 什么"。工作目录：仓库根目录(gold-annotation/)。
这是 gold 数据，宁可弃标(abstain)也不要硬猜。

== 先读两样 ==
1) 角色表：casts/{SOURCE}.json —— 实体清单(canonical)、视角相对称谓、ambiguous 消解、
   倒指代回填、语癖签名。先吃透 focalizer_note / ambiguous / needs_registry。
   注意 cast 里 playable:false / present:false 的群体/路人/未登场者仍要照常标(它们也在场说做)，
   只是下游不为其组装样本——你只管忠实标注。
2) 运行：python3 src/render_chapter.py {CORPUS_DIR}/{SOURCE}.json —— 输出 [全文]每句 `scene_sent│正文`
   (完整上下文) + [待标台词] uid。**scene 头的 [在场] 是机械名匹配的辅助闭集**(present:true 角色)，
   帮你缩小该节说话人候选；但它 recall 取向、可能漏(只靠代词出场者)，**以正文为准**。
   **读完整章再下结论**(倒指代/晚点名要读到后文回填)。

== 抽取规则(按句、多标签、可重复) ==
- 给【全章每一句】产出一条 unit：{uid, text(逐字原文), involves:[{char, role, conf}]}。
- role 只有两种：
    说 = 引号内的**成句口头台词**(说话人)。
    做 = 该角色一切非台词表现：动作 / 神态 / 体态 / 显式内心思绪(明确以角色为主语的思考)
         / **拟声·呜咽·吼叫·咬牙·呵欠等非成句发声**。
  (不设"想"：思考与动作同归"做"。**拟声/发声也归"做"**，参 旅途余白 2_154「唔唔唔」=罗伦斯·做、不标说。)
- 显式施事测试(关键，专治环境烘托过标)：一句只在它显式描写某角色在 说/做(该角色为该子句主语/施事)
  时才进 involves。纯写景/氛围/泛论/叙述者议论——即便隐含焦点者心境——一律 involves:[]，不强归焦点者。
  · 心理活动也走显式施事测试：内心活动**仅在有显式心理动词**(想/觉得/心想/纳闷/猜/感到/想起/不知道/希望/怀疑…)、
    且该角色本人为施事主语时，才算其"做"(conf 降一档 med/low)。**无心理动词的裸命题/泛论/比喻/背景概述
    (即便出自第一人称叙述者之口)→ involves:[]**，不强归。揣测**他人**心理(他人为动词主语)→ 至多他人 做:low 或 []，不挂叙述者。
  · 现场性闸(治非现场动作过标)："做"只给该角色在**本场景当下正在做出**的动作。
    判据看**动作动词本身是否落在非现场算子辖域内**——假设(如果/若是/换作)、习惯频率(总是/向来/经常)、
    回忆闪回(当年/那时/曾经…作往事重述)、未遂意图(打算/正要…却没)、泛述概要(这一路/这些天…一笔带过)。
    - 算子只修饰背景名词/旁支从句、动作词仍在主事件线 → 照常现场"做"(如「原本托着腮的头」里抬头仍是现场，不降)。
    - 动作词在算子辖域内 → 默认 involves:[](纯非现场叙述)或 做:low(现场被概要压缩、拿不准)，**绝不 high**。
    - 混合句(现场动作+非现场议论同句) → "做"只挂现场动作那部分，非现场议论不另标。
    - "现场"相对**所述场景**：闪回被渲染成独立 scene 时，其内部动作照标现场"做"。
- 一句涉及多角色 → involves 列多个(整句重复进各角色，不切分句)。
- char = cast 的 canonical(视角相对称谓归一到所指实体；按场景消解)。群戏无名 → cast 集体实体或 "-"。
- 台词句必恰一个 role=说。但"有引号 ≠ 一定是说"：招牌名/书名/比喻/被引述词/标题等非口头发言的引号，
  按写景或"做"处理，不强标说；无引号的自由间接引语若确为口说，可标说。
  ★同句多引号警觉：一句里既有引号又带"…说/道："标签(引出下句台词)时，本句的引号内容(常是发声/拟声)
   与下句台词分属不同人，别把下句说话人错挂到本句(参 旅途余白 2_154 教训)。
- conf ∈ {high, med, low}，锚弱标 low 或弃标。
- 护栏：单元只记 who + 说/做 + 原文。绝不写动作类型/动机/对谁/因果/情绪标签。

== 输出 ==
写文件 {OUTDIR}/{SOURCE}.json(先 mkdir -p {OUTDIR})。纯 JSON、UTF-8：
{
  "schema_version": "units/0.2",
  "source": "{SOURCE}", "focalizer": "<取自 cast>", "cast_ref": "casts/{SOURCE}.json", "model": "{MODEL}",
  "units": [
    {"uid":"2_44","text":"罗伦斯以指腹滑过那张脸蛋，少女的耳朵随之抽动……",
     "involves":[{"char":"罗伦斯","role":"做","conf":"high"},{"char":"赫萝","role":"做","conf":"high"}]}
  ]
}
- units 覆盖【全章每一句】，uid 顺序与 render 全文一致(含纯写景句 involves:[])。

== 自检后再交 ==
- 句数 = render 全文行数；role 仅 {说,做}；char ∈ cast.canonical ∪ "-"；每句 说≤1。
- 待标台词 uid 里**口头成句发言**者各恰一个说；**拟声/招牌名/比喻/被引述词**等非口头发言**归做或写景，不强标说**
  (别为了"每个待标台词都有说"而硬塞——`units_check` 的「有引号≠说」项就是来收这些的，0 条往往意味着把拟声错标成了说)。
最后用文字返回：①总句数 ②说句数 ③involves 为空句数 ④你最不确定的 3-5 处(uid+原因)
⑤同句多引号/双主角互换里最易错的轮替点。简洁即可。
```

## 注意

- subagent 出**候选**，人来定夺；分歧、low/med-conf、抽检预筛 ⚑ 是给人审的信号，不是失败。
- **不改 `casts/*.json`、不改 `aliases.json`**。units 层只读 cast、只写 `units/`。
- 覆盖必须 = `render_chapter` 全句数，uid 同序；`units_check` 会卡这条。
- 第二模型必须**不同家族、势均力敌**；没有它就只有结构自检、出不了可信 gold。
- 说层回归(`units_check` 里 vs `phase2/`)是**顺手白捡、非支柱**；共谋盲区靠抽检预筛 + `fix` 通道。
