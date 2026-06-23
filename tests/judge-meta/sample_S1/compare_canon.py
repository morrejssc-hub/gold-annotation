#!/usr/bin/env python3
"""给原文 vs 无原文（同为 Claude subagent fan-out）消融对比。"""
import json, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
J = sys.argv[1] if len(sys.argv)>1 else "claude"
print(f"########## 判官 = {J} ##########")
NO = json.loads((HERE/f"scores.{J}.json").read_text())["scores"]       # 无原文
CA = json.loads((HERE/f"scores_canon.{J}.json").read_text())["scores"] # 给原文
KM = json.loads((HERE/"keymap.json").read_text())
bids = sorted(NO, key=lambda b:int(b[1:]))
CP=["Q1","Q4","Q5","Q8"]
def veto(s): return [q for q in CP if s[q]<=2]+(["Q6↑"] if s["Q6"]>=4 else [])
Qs=[f"Q{i}" for i in range(1,11)]

print("=== 逐条逐项：给原文 − 无原文（只列有变化的项） ===")
for b in bids:
    diffs={q:CA[b][q]-NO[b][q] for q in Qs if CA[b][q]!=NO[b][q]}
    vN,vC=veto(NO[b]),veto(CA[b])
    vchg = f"  否决:{vN or '过'}→{vC or '过'}" if vN!=vC else ""
    print(f"  {b}({KM[b]['format'][:2]}): "+(", ".join(f"{q}{d:+d}" for q,d in diffs.items()) if diffs else "无变化")+vchg)

print("\n=== 各 Q 平均绝对变动 ===")
for q in Qs:
    mad=statistics.mean(abs(CA[b][q]-NO[b][q]) for b in bids)
    mean_shift=statistics.mean(CA[b][q]-NO[b][q] for b in bids)
    print(f"  {q}: |Δ|均={mad:.2f}  方向均={mean_shift:+.2f}")

print("\n=== 关注项 ===")
print("  Q7(报菜名)方向: 给原文后若系统性下降=原文味/复刻压力泄漏；上升=判官更认可意象服务")
for tag,q in [("Q1真崩","Q1"),("Q4拒收逼问","Q4"),("Q6现代自白","Q6"),("Q7报菜名","Q7"),("Q10贴合","Q10")]:
    no=statistics.mean(NO[b][q] for b in bids); ca=statistics.mean(CA[b][q] for b in bids)
    print(f"  {tag:10}: 无原文均={no:.2f} → 给原文均={ca:.2f} (Δ{ca-no:+.2f})")

print("\n=== 幸存(单判官口径:无critical否决) 对比 ===")
sN=[b for b in bids if not veto(NO[b])]; sC=[b for b in bids if not veto(CA[b])]
print(f"  无原文幸存: {sN}")
print(f"  给原文幸存: {sC}")
