#!/usr/bin/env python3
"""S1 样板汇总：应用 manifest 的 否决/判官有效性/分轴，并比两判官一致性、按格式分解。
判官：Claude(干净subagent) + GLM。验证目标见 manifest.validation_targets。"""
import json, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
CL = json.loads((HERE/"scores.claude.json").read_text())["scores"]
GL = json.loads((HERE/"scores.glm.json").read_text())["scores"]
KM = json.loads((HERE/"keymap.json").read_text())
bids = sorted(CL, key=lambda b:int(b[1:]))
JUD = {"Claude": CL, "GLM": GL}

CRIT_POS = ["Q1","Q4","Q5","Q8"]   # ≤2 触闸
CRIT_NEG = ["Q6"]                  # ≥4 触闸 (反极性)
HARD = CRIT_POS + CRIT_NEG
SOFT = ["Q3","Q7"]

def vetoed(s):
    bad = [q for q in CRIT_POS if s[q]<=2] + [q for q in CRIT_NEG if s[q]>=4]
    return bad

print("=== 各判官：否决判定（critical正项≤2 或 Q6≥4） ===")
for jn,J in JUD.items():
    print(f"  [{jn}]")
    for b in bids:
        bad=vetoed(J[b]); fmt=KM[b]["format"][:2]
        tag = f"否决←{bad}" if bad else "通过"
        print(f"    {b}({fmt}) Q1={J[b]['Q1']} Q4={J[b]['Q4']} Q5={J[b]['Q5']} Q6={J[b]['Q6']} Q8={J[b]['Q8']} | Q10={J[b]['Q10']} Q9={J[b]['Q9']} → {tag}")

print("\n=== 否决一致性（两判官是否枪毙同一批） ===")
agree=0
for b in bids:
    vc=bool(vetoed(CL[b])); vg=bool(vetoed(GL[b]))
    agree += vc==vg
    if vc!=vg: print(f"  分歧 {b}: Claude={'否' if vc else '过'} GLM={'否' if vg else '过'}")
print(f"  一致 {agree}/9")

print("\n=== 判官有效性红旗（单场景仅观察，不降权） ===")
for jn,J in JUD.items():
    # 通过其它critical的'好答案'里 Q6 是否异常高（无脑给高/迎合）
    good=[b for b in bids if not ([q for q in CRIT_POS if J[b][q]<=2])]
    q6good=[J[b]["Q6"] for b in good]
    # 诱饵Q2 与 Q9/Q10 相关
    q2=[J[b]["Q2"] for b in bids]; q9=[J[b]["Q9"] for b in bids]; q10=[J[b]["Q10"] for b in bids]
    def pear(x,y):
        mx,my=statistics.mean(x),statistics.mean(y); sx,sy=statistics.pstdev(x),statistics.pstdev(y)
        return round(sum((a-mx)*(b-my) for a,b in zip(x,y))/len(x)/(sx*sy),2) if sx and sy else 0.0
    print(f"  [{jn}] 好答案Q6均值={round(statistics.mean(q6good),2) if q6good else '-'}(应低) | 诱饵Q2×Q9={pear(q2,q9)} Q2×Q10={pear(q2,q10)}(应≈0)")

print("\n=== 两判官一致性：各 Q 的平均绝对差（0=完全一致） ===")
for q in [f"Q{i}" for i in range(1,11)]:
    md=statistics.mean(abs(CL[b][q]-GL[b][q]) for b in bids)
    tier = "硬" if q in HARD else ("软" if q in SOFT else ("产品" if q=="Q9" else ("贴合" if q=="Q10" else "诱饵")))
    print(f"  {q}[{tier}]: MAD={md:.2f}")
hard_mad=statistics.mean(abs(CL[b][q]-GL[b][q]) for b in bids for q in HARD)
soft_mad=statistics.mean(abs(CL[b][q]-GL[b][q]) for b in bids for q in SOFT)
print(f"  → 硬项整体 MAD={hard_mad:.2f} | 软项整体 MAD={soft_mad:.2f}（预期 软>硬）")

print("\n=== 新增 critical 项是否真 fire（任一判官触发计） ===")
for q,desc,cond in [("Q5","惰性over-read",lambda v:v<=2),("Q6","现代依赖自白",lambda v:v>=4),("Q8","时代错置",lambda v:v<=2)]:
    hits=[f"{b}({KM[b]['format'][:2]}:C{CL[b][q]}/G{GL[b][q]})" for b in bids if cond(CL[b][q]) or cond(GL[b][q])]
    print(f"  {q} {desc}: {hits if hits else '未触发'}")

print("\n=== 按输出格式：各 Q 均值（两判官合并） ===")
fmts=["F1_resp_only","F2_motive_then_resp","F3_direct_ask"]
print(f"  {'fmt':6} "+" ".join(f"{q:>4}" for q in [f'Q{i}' for i in range(1,11)]))
for fmt in fmts:
    fb=[b for b in bids if KM[b]["format"]==fmt]
    row=[statistics.mean([CL[b][q] for b in fb]+[GL[b][q] for b in fb]) for q in [f"Q{i}" for i in range(1,11)]]
    print(f"  {fmt[:6]:6} "+" ".join(f"{v:>4.1f}" for v in row))
print("  (看 F3: Q6现代自白↑? Q1/Q4真崩↓? Q9深度是否仍不低=膨胀但被硬项摁住)")

print("\n=== 合规幸存者（两判官都不否决）按贴合Q10排序 ===")
surv=[b for b in bids if not vetoed(CL[b]) and not vetoed(GL[b])]
for b in sorted(surv,key=lambda b:-(CL[b]["Q10"]+GL[b]["Q10"])):
    print(f"  {b}({KM[b]['format']}) Q10={CL[b]['Q10']}/{GL[b]['Q10']} Q9={CL[b]['Q9']}/{GL[b]['Q9']} 软Q3={CL[b]['Q3']}/{GL[b]['Q3']} Q7={CL[b]['Q7']}/{GL[b]['Q7']}")
print(f"  幸存 {len(surv)}/9")
