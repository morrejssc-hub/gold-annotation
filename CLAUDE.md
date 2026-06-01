# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 一句话

为《狼与香辛料》语料构建**说话人归属（speaker attribution）的 gold 数据**，给 SFT 产出训练/评测集。任务锚点：给定正文，判断每条台词的说话人。

## 先读这些（细节都在里面，别在 CLAUDE.md 复述）

- [`README.md`](README.md) — 当前架构总览 + 文件清单 + 进展/下一步。**入口**。
- [`DESIGN-PIVOTS.md`](DESIGN-PIVOTS.md) — 为什么转向两次、反复踩的坑。**改架构前必读第 4 节**。
- [`PHASE1.md`](PHASE1.md) — Phase 1 角色表的规范、schema、验证。范例见 `casts/后日谈.json`。
- [`.claude/skills/cast-sheet/SKILL.md`](.claude/skills/cast-sheet/SKILL.md) — Claude 跑 Phase 1 的 subagent 扇出流程。

## 三条不能违反的约束（违反即重蹈覆辙，详见 DESIGN-PIVOTS）

1. 归属是**带状态的篇章级序列标注**，不是单条 i.i.d. 分类（±3 句窗口下约 23% 不可解）。
2. 关系称谓（主人/旅伴/父亲）**视角相对，只进各章 cast 的 `appellations`，绝不进全局 `aliases.json`**（后者只放专名）。
3. **不用 agent、不逐句循环**——整章塞进 context；输出用 uid 键、保留显式 abstain（`-`）。

## 命令

```bash
python3 dialogue.py jsons/后日谈.json          # 机械抽台词（单篇）；--all jsons|maintext 全量
python3 phase1_cast.py jsons/后日谈.json --backend dump   # Phase 1 提示词；--backend claude|bailian|codex 调 API
python3 normalize_casts.py --apply            # 跨卷音译归一（默认 dry-run）
python3 finalize_registry.py --apply          # registry 裁决回写各 cast
# 校验 cast：for f in casts/*.json; do python3 -c "import json;json.load(open('$f',encoding='utf-8'))"||echo BAD $f; done
```

后端 key 环境变量：`ANTHROPIC_API_KEY` / `DASHSCOPE_API_KEY`（百炼）/ `OPENAI_API_KEY`（codex）。

## 数据布局

- `jsons/<篇名>.json` — 番外 45 篇，每篇一表（坏档 `幕间.json` 跳过）。
- `maintext/卷NN.json` — 正文 11 卷，focalizer 全卷为罗伦斯，**按卷一张表**。
- `casts/` Phase 1 产物 → Phase 2 输入；`aliases.json` 全局专名种子；`focalizers.tsv` Phase 0 视角；`eval.tsv`/`sheet.tsv` 人工 gold。
- 结构统一 `doc.scenes[].sents[]`，句号写作 `sceneid_sentid`。
