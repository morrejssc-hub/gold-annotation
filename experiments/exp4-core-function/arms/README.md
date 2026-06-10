# item09 2×2 消融 · 四臂 Runtime 锁版（PLAN §5）

因子 = {Atlas re-type ±} × {core 新两条（目的=核(情景) + veto）±}。四臂统一 `--mode prod`。

| 臂 | re-type | 目的机制 | 构造 |
|---|---|---|---|
| `A.runtime.prod.md` | − | − | exp3 Atlas @ **651d67c**（commit pin），pin 树自带 compile.py 编译 |
| `B.runtime.prod.md` | + | + | 工作树 re-type 后 Atlas + core 新两条，新 compile.py 编译 |
| `C.runtime.prod.md` | + | − | 工作树 re-type 后 Atlas（加新两条**之前**快照），新 compile.py 编译 |
| `D.runtime.prod.md` | − | + | pin 651d67c 树的旧 `spine/core.md` graft 新两条（`## 目的` 段 + `## 禁止` 补 veto 行），pin 树 compile.py 编译 |

## 因子纯净（已机器验证，2026-06-10）

- `diff(C→B) == diff(A→D)`，逐字相同，恰为 5 行（目的段 4 行 + veto 1 行）——2×2 真 factorial。
- 新两条文本**不引 N 编号**（D 臂旧结构无编号化），B/D 逐字共用。
- 编译器版本随 re-type 因子走（A/D 用 pin 树旧 compile.py，B/C 用新版）——版式差异（如"常驻（始终生效）"vs 三段式）属 re-type treatment 的一部分。

## 使用纪律（PLAN §5）

- 每臂 2–3 次独立 subagent 盲生成，场景上文逐字同（卷4 12_119…12_132），链协议用**机制中立模板**。
- 盲判只看回应；目的读数四格勾选先于排序；判后才揭臂号、对正典 held-out（12_133–139）、审链。
- 本目录是**只读锁版**——别手改这四份 runtime；要改去改 Atlas 再重新构造并更新本 README。
