#!/usr/bin/env python3
"""S1 改版样板 · 三判官(Claude/GLM/codex)汇总。
应用 manifest 否决(critical正项Q1Q4Q5Q8≤2 或 反极性Q6≥4)、判官有效性、跨判官一致、格式分解。"""
import json, statistics, itertools
from pathlib import Path
HERE = Path(__file__).resolve().parent
def load(n): return json.loads((HERE/n).read_text())["scores"]
J = {"Claude":load("scores.claude.json"), "GLM":load("scores.glm.json"), "codex":load("scores.codex.json")}
KM = json.loads((HERE/"keymap.json").read_text())
PItems = json.loads((HERE/"judge_payload.json").read_text())["items"]
TRUELEN = {it["id"]: len(it["text"]) for it in PItems}
bids = sorted(next(iter(J.values())), key=lambda b:int(b[1:]))
CRIT_POS=["Q1","Q4","Q5","Q8"]; CRIT_NEG=["Q6"]; HARD=CRIT_POS+CRIT_NEG; SOFT=["Q3","Q7"]
def veto(s): return [q for q in CRIT_POS if s[q]<=2]+[f"{q}↑" for q in CRIT_NEG if s[q]>=4]
def pear(x,y):
    mx,my=statistics.mean(x),statistics.mean(y); sx,sy=statistics.pstdev(x),statistics.pstdev(y)
    return round(sum((a-mx)*(b-my) for a,b in zip(x,y))/len(x)/(sx*sy),2) if sx and sy else 0.0

print("=== 否决判定（每判官） ===")
for jn,S in J.items():
    vs={b:veto(S[b]) for b in bids}
    print(f"  [{jn}] 否决 {sum(1 for b in bids if vs[b])}/9 : "+", ".join(f"{b}{vs[b]}" for b in bids if vs[b]))

print("\n=== 否决一致性（3判官对每段是否同判） ===")
unan=0
for b in bids:
    flags=[bool(veto(J[jn][b])) for jn in J]
    if all(flags)==any(flags): unan+=1
    else: print(f"  分歧 {b}: "+" ".join(f"{jn}={'否' if veto(J[jn][b]) else '过'}" for jn in J))
print(f"  三方一致 {unan}/9")

print("\n=== 跨判官一致性：各 Q 平均成对绝对差(0=全一致) ===")
pairs=list(itertools.combinations(J,2))
for q in [f"Q{i}" for i in range(1,11)]:
    mad=statistics.mean(abs(J[a][b][q]-J[c][b][q]) for a,c in pairs for b in bids)
    tier={**{x:"硬" for x in HARD},**{x:"软" for x in SOFT},"Q2":"诱饵","Q9":"产品","Q10":"贴合"}[q]
    print(f"  {q}[{tier}]: MAD={mad:.2f}")
hard=statistics.mean(abs(J[a][b][q]-J[c][b][q]) for a,c in pairs for b in bids for q in HARD)
soft=statistics.mean(abs(J[a][b][q]-J[c][b][q]) for a,c in pairs for b in bids for q in SOFT)
print(f"  → 硬项 MAD={hard:.2f} | 软项 MAD={soft:.2f}（预期 软>硬）")

print("\n=== 判官有效性红旗 ===")
for jn,S in J.items():
    good=[b for b in bids if not [q for q in CRIT_POS if S[b][q]<=2]]
    q6=[S[b]["Q6"] for b in good]
    q2=[S[b]["Q2"] for b in bids]; q9=[S[b]["Q9"] for b in bids]; q10=[S[b]["Q10"] for b in bids]
    tl=[TRUELEN[b] for b in bids]
    print(f"  [{jn}] 好答案Q6均值={round(statistics.mean(q6),2) if q6 else '-'}(应低) | 诱饵Q2×Q9={pear(q2,q9)} Q2×Q10={pear(q2,q10)}(应≈0) | Q2×真字数={pear(q2,tl)}(应高=判官真在读长度)")

print("\n=== 新增 critical 是否 fire（任一判官） ===")
for q,desc,cond in [("Q5","惰性over-read",lambda v:v<=2),("Q6","现代依赖自白",lambda v:v>=4),("Q8","时代错置",lambda v:v<=2)]:
    hits=[f"{b}({KM[b]['format'][:2]}:"+"/".join(str(J[jn][b][q]) for jn in J)+")" for b in bids if any(cond(J[jn][b][q]) for jn in J)]
    print(f"  {q} {desc}: {hits if hits else '未触发'}")

print("\n=== 按格式：各 Q 均值(3判官合并) ===")
print(f"  {'fmt':6} "+" ".join(f"{q:>4}" for q in [f'Q{i}' for i in range(1,11)]))
for fmt in ["F1_resp_only","F2_motive_then_resp","F3_direct_ask"]:
    fb=[b for b in bids if KM[b]["format"]==fmt]
    row=[statistics.mean(J[jn][b][q] for jn in J for b in fb) for q in [f"Q{i}" for i in range(1,11)]]
    print(f"  {fmt[:6]:6} "+" ".join(f"{v:>4.1f}" for v in row))

print("\n=== 合规幸存者【2/3 多数否决口径】按贴合Q10均值排序 ===")
def nvotes(b): return sum(1 for jn in J if veto(J[jn][b]))
surv=[b for b in bids if nvotes(b)<2]   # <2 票否决 = 幸存
for b in sorted(surv,key=lambda b:-statistics.mean(J[jn][b]["Q10"] for jn in J)):
    q10=statistics.mean(J[jn][b]["Q10"] for jn in J); q9=statistics.mean(J[jn][b]["Q9"] for jn in J)
    print(f"  {b}({KM[b]['format']}) Q10均={q10:.1f} Q9均={q9:.1f} 否决票={nvotes(b)}/3")
print(f"  幸存 {len(surv)}/9 ; 被≥2票否决 {9-len(surv)}/9")
print("  (对照·任一否决口径幸存:", [b for b in bids if nvotes(b)==0], ")")
