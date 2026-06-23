#!/usr/bin/env python3
"""汇总：join scores+keymap，算两量表分歧。"""
import json
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
S = json.loads((HERE / "scores.json").read_text(encoding="utf-8"))["scores"]
KM = json.loads((HERE / "keymap.json").read_text(encoding="utf-8"))

rows = []
for bid, sc in S.items():
    km = KM[bid]
    rows.append({"bid": bid, "scenario": bid.split("-")[0], "format": km["format"],
                 "H": sc["H"], "cl": sc["cl"], "crit": sc["crit"], "viol": sc["viol"]})

def mean(xs): return round(sum(xs) / len(xs), 2) if xs else 0.0

print(f"N = {len(rows)}\n")

# 1) 危险象限：整体高(H>=4) 但 checklist 关键违规
danger = [r for r in rows if r["H"] >= 4 and r["crit"]]
print(f"=== 危险象限 (整体H>=4 且 checklist关键违规) : {len(danger)}/{len(rows)} ===")
print("  这些是'整体打分会放行、checklist 才拦下'的膨胀样本：")
for r in sorted(danger, key=lambda r: (-r["H"], r["bid"])):
    print(f"  {r['bid']:7} H={r['H']} cl={r['cl']} fmt={r['format']:18} viol={r['viol']}")

# 2) 反向象限：整体低(H<=3) 但 checklist 干净（被整体分冤枉的克制正确答案）
wronged = [r for r in rows if r["H"] <= 3 and not r["crit"] and r["cl"] == 5]
print(f"\n=== 被整体分压低的干净克制答案 (H<=3 且 cl=5) : {len(wronged)} ===")
for r in sorted(wronged, key=lambda r: r["bid"]):
    print(f"  {r['bid']:7} H={r['H']} cl={r['cl']} fmt={r['format']}")

# 3) 场景内排序反转：整体榜首 vs checklist 是否一致
print("\n=== 场景内排序反转（整体 top vs checklist） ===")
by_sc = defaultdict(list)
for r in rows: by_sc[r["scenario"]].append(r)
inversions = 0
for s in sorted(by_sc):
    items = by_sc[s]
    topH = max(items, key=lambda r: (r["H"], -["F1_resp_only","F2_motive_then_resp","F3_direct_ask"].index(r["format"])))
    # 该场景里 H 最高的若干（并列）
    hmax = max(r["H"] for r in items)
    top_hits = [r for r in items if r["H"] == hmax]
    crit_in_top = [r for r in top_hits if r["crit"]]
    clean = [r for r in items if not r["crit"]]
    clean_max_H = max((r["H"] for r in clean), default=0)
    flag = ""
    if crit_in_top:
        inversions += 1
        flag = f"  <== 整体榜首含关键违规 {[r['bid'] for r in crit_in_top]}；干净答案最高仅 H={clean_max_H}"
    print(f"  {s}: H_top={hmax} (并列{len(top_hits)}) 其中关键违规{len(crit_in_top)}个{flag}")
print(f"  反转场景数: {inversions}/{len(by_sc)}")

# 4) 相关性（Spearman 粗算用 Pearson on ranks 略；这里给 H 与 cl 的简单相关 + 分桶）
import statistics
Hs = [r["H"] for r in rows]; Cls = [r["cl"] for r in rows]
mh, mc = mean(Hs), mean(Cls)
cov = sum((r["H"]-mh)*(r["cl"]-mc) for r in rows)/len(rows)
sh = statistics.pstdev(Hs); scl = statistics.pstdev(Cls)
pearson = round(cov/(sh*scl), 3) if sh and scl else 0.0
print(f"\n=== 全局相关 H vs cl ===")
print(f"  mean H={mh}  mean cl={mc}  Pearson(H,cl)={pearson}  (接近0=两量表几乎无关)")

# 5) 按格式分解：膨胀是否随'诊断/直白'格式上升
print("\n=== 按输出格式分解（核验：格式是否把膨胀漏进回应） ===")
print(f"  {'format':20} {'n':>3} {'meanH':>6} {'crit率':>7} {'meanCl':>7} {'危险象限':>8}")
for fmt in ["F1_resp_only", "F2_motive_then_resp", "F3_direct_ask"]:
    fr = [r for r in rows if r["format"] == fmt]
    critrate = round(sum(r["crit"] for r in fr)/len(fr), 2)
    dz = sum(1 for r in fr if r["H"]>=4 and r["crit"])
    print(f"  {fmt:20} {len(fr):>3} {mean([r['H'] for r in fr]):>6} {critrate:>7} {mean([r['cl'] for r in fr]):>7} {dz:>8}")

# 6) 关键违规计数 by forbidden id
print("\n=== 触发的关键违规分布（按 forbidden id） ===")
vc = defaultdict(int)
for r in rows:
    for v in r["viol"]: vc[v]+=1
for k in sorted(vc): print(f"  {k}: {vc[k]}")
