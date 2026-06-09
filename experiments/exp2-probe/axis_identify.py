"""R0′ 地基诊断：所谓「trust 轴」可辨识吗？（仅用 acts.npz，离线可算）

问三件事，回答「这条 d 是不是一条能辨识为 trust 专属的线性轴」：
  1. 可复现性：把 6 高 6 低各劈成 3+3，独立算两条 d，夹角余弦（拆半自相关）；
     对随机打乱 label 的零假设比——高于零假设才算「不是噪声」。
  2. 混杂：cos(d_trust, d_third_person) / cos(d_trust, d_tone柔软)——
     |cos|→1 即 trust 方向与该混杂轴近共线，diff-of-means 切不开。
  3. 跨层：在 steering 用过的层（L6/L38）+ 语气纠缠层（L26）都报一遍。

用法: python axis_identify.py            # 默认读同目录 acts.npz / samples.jsonl
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def dv(A, lab, L):
    return A[lab == 1, L].mean(0) - A[lab == 0, L].mean(0)


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def splithalf(acts, labels, L, rng, nrep=500):
    """6 高 6 低各劈 3+3，两半独立估 d，夹角余弦的均值±std。"""
    h = np.where(labels == 1)[0]
    l = np.where(labels == 0)[0]
    cs = []
    for _ in range(nrep):
        ph, pl = rng.permutation(h), rng.permutation(l)
        dA = acts[ph[:3], L].mean(0) - acts[pl[:3], L].mean(0)
        dB = acts[ph[3:], L].mean(0) - acts[pl[3:], L].mean(0)
        cs.append(cos(dA, dB))
    return float(np.mean(cs)), float(np.std(cs))


def nullsplit(acts, y, L, rng, nrep=500):
    """随机打乱 trust label 后的拆半自相关——可辨识性的零假设。"""
    cs = []
    for _ in range(nrep):
        yp = rng.permutation(y)
        h, l = np.where(yp == 1)[0], np.where(yp == 0)[0]
        ph, pl = rng.permutation(h), rng.permutation(l)
        dA = acts[ph[:3], L].mean(0) - acts[pl[:3], L].mean(0)
        dB = acts[ph[3:], L].mean(0) - acts[pl[3:], L].mean(0)
        cs.append(cos(dA, dB))
    return float(np.mean(cs)), float(np.std(cs))


def main():
    acts = np.load(HERE / "acts.npz")["acts"]
    S = [json.loads(x) for x in (HERE / "samples.jsonl").open(encoding="utf-8")]
    y = np.array([1 if s["trust"] == "high" else 0 for s in S])
    tp = np.array([1 if s["third_person"] else 0 for s in S])
    tone = np.array([1 if s["tone"] == "柔软" else 0 for s in S])
    rng = np.random.default_rng(0)

    print("layer | cos(trust,3rd) | cos(trust,柔软) | 拆半自相关(trust) | 零假设(随机label)")
    for L in [6, 26, 38]:
        dt, d3, dto = dv(acts, y, L), dv(acts, tp, L), dv(acts, tone, L)
        sh = splithalf(acts, y, L, rng)
        nu = nullsplit(acts, y, L, rng)
        print(f"  L{L:<3d}|  {cos(dt, d3):+.3f}       |   {cos(dt, dto):+.3f}        "
              f"|  {sh[0]:+.3f}±{sh[1]:.2f}   |  {nu[0]:+.3f}±{nu[1]:.2f}")
    print("\n判读：拆半 >> 零假设=方向真实可复现；|cos(trust,3rd)|~0.93=与在场结构近共线，"
          "拿到的是「trust + 在场结构」混合轴，非纯 trust。")


if __name__ == "__main__":
    main()
