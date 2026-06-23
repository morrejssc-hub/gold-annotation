#!/usr/bin/env python3
"""拼 GPT 判官 packet：盲题(pool.blind.md) + 两套量表 + 各场景禁止错误checklist(来自probes.json)。
不含 keymap / 我的判分。GPT 用同一套 bid 输出可解析 JSON，便于跨判官对比。"""
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / "probes.json").read_text(encoding="utf-8"))
pool = (HERE / "pool.blind.md").read_text(encoding="utf-8")

# 解析 pool.blind.md：按场景抓 ### [bid] 块
blocks = {}  # scenario_id -> list[(bid, text)]
cur_sc = None
for chunk in re.split(r"\n## (S\d) 场景\n", pool)[1:]:
    pass
# 简单两段解析
parts = re.split(r"\n## (S\d) 场景\n", pool)
# parts[0]=头部; 之后 (scid, body) 成对
for i in range(1, len(parts), 2):
    scid = parts[i]; body = parts[i+1]
    items = re.findall(r"### \[(S\d-[a-i])\]\n(.*?)(?=\n### \[|\Z)", body, re.S)
    blocks[scid] = [(bid, t.strip()) for bid, t in items]

SC = {s["id"]: s for s in P["scenarios"]}

out = []
out.append("# 赫萝扮演 · 盲评判官任务（GPT）\n")
out.append("""你是一个独立判官。下面每个场景给出若干段“赫萝（《狼与辛香料》女主角）的回应”，每段一个编号（如 S5-e）。这些回应的来源/格式已隐藏并打乱，你只看回应本身。

请对**每一段**给出两套独立评分：

**量表A · 整体印象（1-5 整数）**：作为读者，这段赫萝回应多打动你 / 多有深度 / 多像真正的赫萝？只凭整体感觉打分，**先打完 A 再看量表 B 的 checklist**，不要让 checklist 影响 A。

**量表B · 禁止错误 checklist（每场景给定）**：逐条核对该场景下列“禁止错误”是否出现。
- 标出违规的条目编号（如 ["S5a"]），没有就 []。
- 任一 **critical** 条目被违规 → `crit=true`。
- `cl` 分（1-5）：5=无违规；4=仅非critical违规；2=一条critical违规；1=critical+附加。

**输出格式**：最后输出一个 JSON（且只输出这个 JSON），形如：
```json
{"<编号>": {"H": <1-5>, "viol": ["<违规条目id>", ...], "crit": <true/false>, "cl": <1-5>}, ...}
```
（上面是格式示意，别照抄数字）覆盖全部 63 个编号。
""")

for s in P["scenarios"]:
    sc = SC[s["id"]]
    out.append(f"\n---\n\n## 场景 {sc['id']}\n")
    out.append(f"**情景**：{sc['scene']}\n")
    out.append(f"**正典里她实际怎么演（仅供量表B参照，量表A打分时别看这条）**：{sc['canon_gt']}")
    out.append(f"**可接受的延展**：{sc['acceptable']}\n")
    out.append("**禁止错误（量表B checklist）**：")
    for fb in sc["forbidden"]:
        tag = "【critical】" if fb["critical"] else "【非critical】"
        out.append(f"- `{fb['id']}` {tag} {fb['text']}")
    out.append("\n**待判回应**：")
    for bid, text in blocks[sc["id"]]:
        out.append(f"\n### [{bid}]\n{text}\n")

(HERE / "gpt_judge_packet.md").write_text("\n".join(out), encoding="utf-8")
n = sum(len(v) for v in blocks.values())
print(f"wrote gpt_judge_packet.md ({n} items across {len(blocks)} scenarios)")
