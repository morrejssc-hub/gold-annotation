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
| `jsons/<篇名>.json` | **小说正文素材**（45 篇，`scenes[].sents[]`）。Phase 1/dialogue 的输入；坏档 `幕间.json` 跳过。 |
| `aliases.json` | 全局**专名**别名表（不放代词/关系称谓）。Phase 1 角色表的种子。已含跨卷音译变体归一与 `_note_艾普`。 |
| `casts/<篇名>.json` | **Phase 1 产物**：每章一张角色表（44/44 已生成、人工核验）。Phase 2 输入。 |
| `registry_review.tsv` | needs_registry 人工裁决总账（58 条，verdict=drop/keep_local/resolve）。已回写进各 cast，仅作审计留存。 |
| `normalize_casts.py` | 跨卷音译归一脚本（canonical 取官方名、变体进 aka）。 |
| `finalize_registry.py` | 把 `registry_review.tsv` 裁决回写各 cast 的 needs_registry，使每份 cast 自足。 |
| `dialogue.py` | 纯机械抽取：台词 + 确定性 uid + 上下文窗口（独立可跑）。 |
| `dialogue_all.tsv` | 全量已抽台词（`python3 dialogue.py --all jsons`）。 |
| `focalizers.tsv` | Phase 0：每篇视角角色（手填；Phase 1 已校正 10 行，note 标 `[Phase1校正]`）。 |
| `eval.tsv` | 人工 gold（86 行已核）：验证集 + 本次转向的证据。 |
| `sheet.tsv` | Pivot 0 累积人工 gold（gold_speaker 可复用）。 |

## 进展

- **Phase 1 完成**：`casts/` 覆盖全部 44 章（坏档 `幕间.json` 跳过），JSON 全部合法、已人工核验。详见 [`PHASE1.md`](PHASE1.md) 的「进展」。
- focalizer 校正 10 篇、跨卷音译归一、needs_registry 58 条全部人工 check。每份 cast 自足（无需外部总账即可进 Phase 2）。

## 下一步

进入 **Phase 2**：以 `casts/<篇名>.json`（小角色表）+ `dialogue.py` 抽出的带 uid 台词 + 滚动状态 → `uid→speaker`（窗口化、id 键、可续）。建议先在 `eval.tsv` 已核章上验证覆盖率。
