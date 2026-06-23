#!/usr/bin/env python3
"""跨判官对比：Claude(我) vs GPT。
我的量表：H=整体印象(naive '深度/打动'), cl=禁止错误checklist。
GPT量表：overall=整体(它定义为'像不像这个场景的赫萝'=canon-fidelity), cl=同一checklist。
注意两个'整体'列不是同一把尺（我=深度/打动，GPT=正典贴合度）——见报告。"""
import json, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ME = json.loads((HERE / "scores.json").read_text(encoding="utf-8"))["scores"]
GPT = json.loads((HERE / "scores.gpt.json").read_text(encoding="utf-8"))["scores"]
KM = json.loads((HERE / "keymap.json").read_text(encoding="utf-8"))
bids = sorted(ME)

def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x-mx)*(y-my) for x, y in zip(xs, ys))/len(xs)
    sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    return round(cov/(sx*sy), 3) if sx and sy else 0.0

me_H  = [ME[b]["H"] for b in bids]
me_cl = [ME[b]["cl"] for b in bids]
g_ov  = [GPT[b]["overall"] for b in bids]
g_cl  = [GPT[b]["cl"] for b in bids]

print(f"N = {len(bids)}\n")
print("=== 相关矩阵（Pearson） ===")
print(f"  我checklist  vs GPTchecklist : {pearson(me_cl, g_cl):+.3f}   <-- checklist 跨判官是否稳")
print(f"  GPT整体      vs GPTchecklist : {pearson(g_ov, g_cl):+.3f}   <-- GPT内部两列(它整体=正典贴合)")
print(f"  我整体(H)    vs 我checklist  : {pearson(me_H, me_cl):+.3f}   <-- 我内部两列(我整体=深度/打动)")
print(f"  我整体(H)    vs GPT整体      : {pearson(me_H, g_ov):+.3f}   <-- 两个'整体'列(不同尺)")
print(f"  我整体(H)    vs GPTchecklist : {pearson(me_H, g_cl):+.3f}")
print(f"  我checklist  vs GPT整体      : {pearson(me_cl, g_ov):+.3f}")

# 危险象限：我标的'整体高(H>=4)且关键违规'样本，GPT两列怎么打？
print("\n=== 我的危险象限(H>=4且crit) 在 GPT 眼里 ===")
print("  bid     我H 我cl | GPT整体 GPTcl  fmt")
danger = [b for b in bids if ME[b]["H"] >= 4 and ME[b]["crit"]]
gpt_killed = 0
for b in danger:
    g = GPT[b]
    killed = g["overall"] <= 3 and g["cl"] <= 3
    gpt_killed += killed
    mark = "  <-- GPT两列都压低(≤3)" if killed else ""
    print(f"  {b:7} {ME[b]['H']:>3} {ME[b]['cl']:>4} | {g['overall']:>6} {g['cl']:>5}  {KM[b]['format']:18}{mark}")
print(f"  GPT 在两列都压低的比例: {gpt_killed}/{len(danger)}")

# 我标干净克制(cl=5)但我整体压低(H<=3)的：GPT 是否也给高/中？
print("\n=== 我'克制正确(cl=5)却被我整体压低(H<=3)'的样本，GPT 怎么看 ===")
wronged = [b for b in bids if ME[b]["cl"] == 5 and ME[b]["H"] <= 3]
rescued = 0
for b in wronged:
    g = GPT[b]
    r = g["overall"] >= 3.5
    rescued += r
    print(f"  {b:7} 我H={ME[b]['H']} | GPT整体={g['overall']} GPTcl={g['cl']}  fmt={KM[b]['format']}" + ("  <-- GPT整体给回≥3.5" if r else ""))
print(f"  GPT整体给回(≥3.5)的比例: {rescued}/{len(wronged)}")

# 每场冠军是否一致
print("\n=== 每场冠军（按各自 checklist 取最高，并列列出） ===")
from collections import defaultdict
def champs(scoremap, key):
    by = defaultdict(list)
    for b in bids: by[b.split("-")[0]].append(b)
    out = {}
    for s, items in by.items():
        m = max(scoremap[b][key] for b in items)
        out[s] = [b for b in items if scoremap[b][key] == m]
    return out
mc = champs(ME, "cl"); gc = champs(GPT, "cl")
for s in sorted(mc):
    inter = set(mc[s]) & set(gc[s])
    print(f"  {s}: 我={mc[s]}  GPT={gc[s]}  交集={sorted(inter) if inter else '∅'}")

# 按格式：GPT 的 checklist 也该 F3 最差
print("\n=== 按输出格式（GPT 视角，复核 F3 漏膨胀） ===")
print(f"  {'format':20} {'n':>3} {'GPT整体':>7} {'GPTcl':>7} {'我H':>5} {'我cl':>5}")
for fmt in ["F1_resp_only", "F2_motive_then_resp", "F3_direct_ask"]:
    fb = [b for b in bids if KM[b]["format"] == fmt]
    print(f"  {fmt:20} {len(fb):>3} {statistics.mean(GPT[b]['overall'] for b in fb):>7.2f} {statistics.mean(GPT[b]['cl'] for b in fb):>7.2f} {statistics.mean(ME[b]['H'] for b in fb):>5.2f} {statistics.mean(ME[b]['cl'] for b in fb):>5.2f}")
