#!/usr/bin/env python3
"""三判官对比：Claude / GPT / GLM。
列：
  ME.H   = 我·深度整体(危险量表)        ME.cl  = 我·checklist
  GPT.ov = GPT·贴合整体(它自定义)        GPT.cl = GPT·checklist
  GLM.A  = GLM·深度整体(写死)            GLM.B = GLM·贴合整体(写死)   GLM.cl = GLM·checklist
关键：GLM 同一判官内同时有 A(深度)与 B(贴合)，可在'判官固定'下隔离量表效应。"""
import json, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ME  = json.loads((HERE / "scores.json").read_text())["scores"]
GPT = json.loads((HERE / "scores.gpt.json").read_text())["scores"]
GLM = json.loads((HERE / "scores.glm.json").read_text())["scores"]
KM  = json.loads((HERE / "keymap.json").read_text())
bids = sorted(ME)

def col(src, key): return [src[b][key] for b in bids]
def pear(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    return round(sum((x-mx)*(y-my) for x,y in zip(xs,ys))/len(xs)/(sx*sy), 3) if sx and sy else 0.0

cols = {"ME.H": col(ME,"H"), "ME.cl": col(ME,"cl"),
        "GPT.ov": col(GPT,"overall"), "GPT.cl": col(GPT,"cl"),
        "GLM.A": col(GLM,"A"), "GLM.B": col(GLM,"B"), "GLM.cl": col(GLM,"cl")}

print(f"N = {len(bids)}\n")
print("=== ① 单判官内·量表效应（GLM 固定判官，三列） ===")
print(f"  GLM 深度A × checklist : {pear(cols['GLM.A'], cols['GLM.cl']):+.3f}   (深度 vs 清单)")
print(f"  GLM 贴合B × checklist : {pear(cols['GLM.B'], cols['GLM.cl']):+.3f}   (贴合 vs 清单)")
print(f"  GLM 深度A × 贴合B     : {pear(cols['GLM.A'], cols['GLM.B']):+.3f}   (两种整体彼此)")
print("  → 若 A×cl 低、B×cl 高，则'量表锚在哪'在同一判官内就分裂两列 = 纯量表效应，无判官混淆")

print("\n=== ② 同尺换判官·量表效应是否复现 ===")
print(f"  深度整体:  ME.H × GLM.A   : {pear(cols['ME.H'], cols['GLM.A']):+.3f}")
print(f"  贴合整体:  GPT.ov × GLM.B : {pear(cols['GPT.ov'], cols['GLM.B']):+.3f}")
print(f"  深度 vs 贴合(跨判官): ME.H × GLM.B : {pear(cols['ME.H'], cols['GLM.B']):+.3f}")

print("\n=== ③ checklist 三判官两两一致 ===")
print(f"  ME.cl × GPT.cl : {pear(cols['ME.cl'], cols['GPT.cl']):+.3f}")
print(f"  ME.cl × GLM.cl : {pear(cols['ME.cl'], cols['GLM.cl']):+.3f}")
print(f"  GPT.cl × GLM.cl: {pear(cols['GPT.cl'], cols['GLM.cl']):+.3f}")

print("\n=== ④ 全相关矩阵 ===")
names = list(cols)
print("        " + " ".join(f"{n:>7}" for n in names))
for a in names:
    print(f"  {a:6} " + " ".join(f"{pear(cols[a],cols[b]):>7.2f}" for b in names))

print("\n=== ⑤ 按输出格式：各列均分（验 F3 漏膨胀 + 深度列奖励它） ===")
print(f"  {'format':20} " + " ".join(f"{n:>6}" for n in names))
for fmt in ["F1_resp_only", "F2_motive_then_resp", "F3_direct_ask"]:
    fb = [b for b in bids if KM[b]["format"] == fmt]
    row = []
    for n in names:
        src = {"ME.H":(ME,"H"),"ME.cl":(ME,"cl"),"GPT.ov":(GPT,"overall"),"GPT.cl":(GPT,"cl"),
               "GLM.A":(GLM,"A"),"GLM.B":(GLM,"B"),"GLM.cl":(GLM,"cl")}[n]
        row.append(statistics.mean(src[0][b][src[1]] for b in fb))
    print(f"  {fmt:20} " + " ".join(f"{v:>6.2f}" for v in row))

print("\n=== ⑥ 我的危险象限(H>=4&crit) 在 GLM 三列 ===")
print(f"  {'bid':7} {'ME.H':>4} {'A':>4} {'B':>4} {'cl':>4}  fmt")
dz = [b for b in bids if ME[b]["H"]>=4 and ME[b]["crit"]]
killB = killcl = highA = 0
for b in dz:
    g = GLM[b]; a,bb,c = g["A"],g["B"],g["cl"]
    highA += a>=4; killB += bb<=3; killcl += c<=3
    print(f"  {b:7} {ME[b]['H']:>4} {a:>4} {bb:>4} {c:>4}  {KM[b]['format']}")
print(f"  GLM深度A仍给高(≥4): {highA}/{len(dz)} | GLM贴合B压低(≤3): {killB}/{len(dz)} | GLM清单cl压低(≤3): {killcl}/{len(dz)}")
