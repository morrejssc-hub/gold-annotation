# Phase 1 · 角色表（cast sheet）

每章**一次**：整章正文 + focalizer → 一张角色表。这是"先确认角色表，再标注"里的"角色表"。
解决四件局部窗口解决不了的事：①倒指代回填 ②视角相对称谓(主人/旅伴/父亲) ③泛称按场景消解 ④跨章点名。
**非 agent、非逐句**——整章塞进 context，一次调用即可；产物小、可人工秒审。

## 工具

```bash
# A) dump 模式: 只生成提示词(无需 key)，可直接贴进 Claude Max
python3 phase1_cast.py jsons/后日谈.json --backend dump > prompt.txt

# B) 直接调 API（产物落 casts/<篇名>.json）
python3 phase1_cast.py jsons/后日谈.json --backend bailian --model qwen-max
python3 phase1_cast.py jsons/后日谈.json --backend codex   --model gpt-4o
python3 phase1_cast.py jsons/后日谈.json --backend claude  --model claude-opus-4-8
```

后端 key 用环境变量：`DASHSCOPE_API_KEY`(百炼) / `OPENAI_API_KEY`(codex) / `ANTHROPIC_API_KEY`(claude)。
focalizer 自动从 `focalizers.tsv` 读取并注入；canonical 种子取自 `aliases.json`。

## 产物 schema

见 `casts/后日谈.json`（标准范例）。每个实体核心字段：

| 字段 | 含义 |
|---|---|
| `canonical` | 归一后的标准名（Phase 2 标注就输出它）。优先专名。 |
| `aka` | 所有**专名/别名/绰号**（可进全局别名表的那种）。 |
| `appellations` | **关系/职务称谓**：主人、祭司大人、旅伴、父亲…**视角相对，不进全局表**。 |
| `descriptors` | 叙述里的描述性/比喻指代：女子、如狼般的女子、那只羊。 |
| `present` / `present_scope` | 是否登场（可能有台词）/ 出现范围。仅被提及=false。 |
| `playable`（可选，缺省 true） | 是否可作角色扮演样本对象。群体/路人/背景（…老板们、议长、领路祭司、马、狼群）标 false；配 `playable_note`。Units 层 `units_assemble` 据此（及 `present:false`）跳过。详见 [`UNITS.md`](UNITS.md)。 |
| `speech` | 语癖/口吻签名（供 Phase 2 判说话人，如赫萝：汝/咱/呐）。 |
| `evidence.first_mention / first_named` | **倒指代证据**：首次出现 vs 首次点名的句号。 |

章级两个特殊区：
- `ambiguous`：泛称（"女子"）随场景指不同人 → Phase 2 按场景消解，不静态映射。
- `needs_registry`：本章正文不点名、需外部判断的项。经人工核验后，每条带：
  - `reviewed`: `人工已核`
  - `verdict`: `resolve`（已确认为某 canonical）/ `keep_local`（篇内无名实体，保留职务名）/ `drop`（背景/非角色，无须处理）
  - `resolution`: 人工裁决说明（含归一到的 canonical）
  - 总账见 `registry_review.tsv`，但裁决已回写各 cast，**每份 cast 自足**。

## 后日谈 验证（已跑通）

focalizer=艾尼克(狗)。角色表把你 `eval.tsv` 里的**视角相对 gold 归一到 canonical**，并解出你标的倒指代行：

| eval.tsv 行 | 你的 gold（视角相对） | 角色表归一 | 备注 |
|---|---|---|---|
| `1_33` | 主人 | **诺儿菈** | appellation 主人→诺儿菈 |
| `1_11` | 女子 | **里夫金女士** | 场景1 泛称消解 |
| `1_34` | 女子 | **里夫金女士** | ★你标「需要扩展context」的倒指代：里夫金名字到 1_27 才出现，回填成功 |

`needs_registry` 也抓到了场景9"女祭司/银器工艺师"——本章不点名，需系列正典（≈艾尔莎/芙兰）确认。

## 进展（2026-05-30）

Phase 1 **全量完成**：`casts/` 覆盖全部 44 章（坏档 `幕间.json` 跳过），JSON 全部合法、人工核验。

- **生成**：Claude subagent 扇出（cast-sheet skill），独立番外 22 篇优先、其余 18 篇随后，每批 ≤3 并行。
- **focalizer 校正（10 篇，已回写 `focalizers.tsv`）**：橡实面包/白色的道路/红霞色的礼物/羊毛刷/苹果的红天空的蓝→罗伦斯；泉烟彼方→瑟莉姆；另一个生日→柯尔；彩虹色的音乐→无名乐师(非艾尼克)；白色的猎犬→格兰·萨尔加多；黑狼的摇篮→艾普。
- **跨卷音译归一**（`normalize_casts.py`）：缪莉→缪里、寇尔→柯尔、艾莉莎→艾尔莎、赫罗→赫萝、鲁华→鲁瓦德、赛莉姆/塞莉姆→瑟莉姆。canonical 取官方名、变体进 aka；`aliases.json` 同步补全。
- **艾普=芙露露(フルール/Fleur)**：经人工定夺全语料 canonical 统一用「艾普」（沿用 后日谈/eval gold）。
- **needs_registry 58 条全部人工 check**（`registry_review.tsv` → `finalize_registry.py` 回写）：31 drop / 14 keep_local / 13 resolve。resolve 中有台词者已在 cast 建 present 实体（如 彩虹色音乐 +诺儿菈/艾尼克/狄安娜/艾尔莎；泉烟彼方 +修斯/希尔德），仅提及者 note 记身份。新具名实体已入 aliases：诺儿菈、艾尼克、米里、攸葛、修斯。

> 一处待定：银器工艺师 canonical 取 `芙兰`（用户记作「芭兰」，已入变体），若官方为芭兰再翻转。

## 下一步

做 **Phase 2**：角色表(`casts/<篇名>.json`) + 带 uid 台词 + 滚动状态 → `uid→speaker`（窗口化、id 键、可续）。先在 `eval.tsv` 已核章上验证覆盖率。
