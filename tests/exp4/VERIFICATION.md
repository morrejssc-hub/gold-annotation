# exp4 自建 Atlas · 实证状态总账（verified / declarative / pending）

> 2026-06-10 起：**exp3 目录冻结为历史**（含其 atlas 与 runtime，不再修改）；exp4 在本目录自建一套 `atlas/` + 编译器。
> 每张卡 frontmatter 的 `verification` 字段记实证状态，本文件是总账与验收路径。
> 原则：**换地基不拆房子**——行为载荷（触发卡）原样平移，重写的只有生成元层（core）。

## verified（行为载荷经 exp1–3 人判闭环实证，本次平移零漂移——diff 验证）

| 卡 | 实证来源 |
|---|---|
| authority-relax | item03 人判 |
| confirm-care | bible_v1 闭环（derivation：**可全推，压缩候选**） |
| crisis-disclosure-gate | item05 盲判胜（重残差，不可压缩） |
| feast-indulge | bible_v1 闭环 |
| human-hypocrisy | item11 v2.2（知识性残差） |
| leak-then-reclaim | item06/item09 两轮人判（含残差） |
| pelt-nerve | bible_v1 闭环（轻残差） |
| praised-deflect | bible_v1 闭环（derivation：**可全推，压缩候选**） |
| unworthy-opponent-disdain | item11 v2.2 |
| wolf-not-tribe | bible_v1 闭环（**负知识卡，不可推亦不可压缩**） |
| output-bans（P1–P3） | item01 失败蒸馏；法层本轮未重组 |
| trust-response | item06 v2.0 + exp2 实证（trust 拆半函数侧） |
| relationship-stance | bible_v1 闭环（derivation：**可全推，压缩候选**——负禁令保留） |

## declarative（描述声明 / 实例绑定，免行为验证）

axes/{presence, pressure, relation}、spine/trust-axis（轴声明，SCHEMA 免锚）；substrate/holo（本体实例；v3 补 R1/R2 实例绑定：故友之托、寻旧友、贤狼之傲——锚卷1_34_125、卷1_8_58 已验证命中）。

## pending（v3 新内容，验收路径见下）

| 项 | 内容 | 验收 |
|---|---|---|
| core v3 双根 | R1 孤独诅咒（双极）/ R2 正面骄傲；N1–N6 降定理层（编号语义不变）；挂根判定 + 对撞拒 + 反偷换 + 分根激活门槛；lie 函数/参数拆分（作用域限 R1） | ①纸面体检 [probes/paper-check.md](probes/paper-check.md)：**已完成，23/23 过、0 退化，待用户签收**；②round1 全 14 条回归重跑（拆墙协议）；③round2 实跑（证伪力降级 caveat 见 paper-check §5.3）；④item09 消融（C/B 臂以本 atlas 重新快照，A/D 与机制因子五行不动） |
| 各卡 derivation 标注 | 10 触发卡 + 3 spine 卡的根推导出处（可全推 / 含残差） | 人审（用户读一遍签收）；压缩动作（可全推卡降判例）排在生成元层过 agent 闸**之后**，每删一批回归一次 |
| N4/N5 拆解标注 | N4 受用面亲密专属 + 索取多源；N5 端面/手段面分离 | 随 core 体检一并验收 |

## 验收流水线（依次，前一步过才走下一步）

1. ✅ 纸面体检（paper-check.md）——待用户签收
2. ✅ **round1 双臂回归已跑**（用户指示先行；[probes/runs/round1-bareR.md](probes/runs/round1-bareR.md)）：裸R 8/14 ≥ 全量 7/14（v2 基线 4–5/14）。读法分支 1 → **建议 N 移出 runtime**；新主导失败模式 = 端法互渗；修法清单 A–E 在报告
3. ✅ **定稿 v3.1 已落卡并 commit**（用户拍板 2026-06-11）：N 移出 runtime（core 笔记段保引用键）+ 修法 A（lie 端法明确化，core）/ B（"演"的边界，output-bans）/ C（禁令作用域，compile.py + SCHEMA 不变量7）/ D（SPEC §5.5/5.6）。三笔 commit：基重写+体检 → 双臂实验 → 定稿（diff 各自可审）
4. **当前位置：round2 实跑前置**——P07 法墙 P3 之争待用户裁决（E，全量臂三轮一致判违）；裁决后跑 round2（18 条，被测 = v3.1）——重点观察族5 假阳性、修法 B 是否治住法墙同型错、P12 误杀是否复发
5. item09 2×2 消融（C/B 重快照，用 v3.1）+ 新域场景 → FINDINGS 收口
