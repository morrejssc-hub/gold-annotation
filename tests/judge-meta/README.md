# tests/judge-meta · judge 元评测

**职责（目录声明，遵教训8）**：验证"危险偏差是否需要按禁止错误 checklist 打分、整体印象打分会不会放行膨胀"。这是 eval 三件套里**评测协议**那一支的预研——不动 active 圣经/prompt，只确定"用哪套量表判"。

不是测被测模型好坏，是测**量表**：同一批 actor 输出、同一个 judge，换量表会不会翻案。

## 文件

| 文件 | 作用 |
|---|---|
| `probes.json` | 探针库（Document A 第一笔）：7 场景 × 正典 GT × 禁止错误 checklist（critical/非critical）× 3 输出格式的 system。gen/clip/tally 共用真源 |
| `gen.py` | actor 生成：deepseek-v4-pro × 7场景 × 3格式 × n=3 = 63 发（DeepSeek 官方 API，urllib）→ `raw.jsonl` |
| `clip.py` | 裁回应段、去标签、组内打乱 → `pool.blind.md`（判官只读）+ `keymap.json`（隐藏映射） |
| `scores.json` | judge（Claude 主会话）两遍盲判结果：整体印象 H(1-5) + checklist 违规/cl分 |
| `tally.py` | join 分数+keymap，算分歧指标 |
| `REPORT.md` | 早期 7 场景三判官结论 |
| `PROTOCOL.md` | **确认流程 / Document C 评测协议雏形**（先读这个） |
| `sample_S1/` | 按协议做的完整样板：probe 修订 + 关系状态头/惰性诱饵 + 三判官逐条 fan-out + 给原文消融 + 合成反例验闸 + 2/3 多数否决。内含 sim_prompt/eval_prompt/manifest 与各阶段 REPORT |

## 纪律

- 判官 = Claude 主会话直判（**不走 subagent**，遵教训7：判定不用会被 harness 提示词污染的 subagent）。
- 判分时只读 `pool.blind.md`，格式+样本号已盲化打乱，判完才解封 `keymap.json`。
- key 文件 `tests/exp4/.deepseek_key` 已 gitignore；`raw.jsonl` 含原始返回留痕。

## 复跑

```
python3 gen.py     # 已有 raw.jsonl 则断点续；删掉重跑
python3 clip.py    # 重新裁剪+盲化（seed 固定，可复现打乱）
# 人工判 pool.blind.md → 改 scores.json
python3 tally.py
```
