#!/usr/bin/env python3
"""units_diff.py —— 比对两份 units/<model>/<篇>.json，按句对 (char,role) 三元组求分歧，分桶 + 出审计清单。
用法: python3 units_diff.py units/claude/旅途余白.json units/gpt/旅途余白.json [--tsv audit.tsv]
"""
import json, sys, argparse
from collections import Counter

def load(p):
    d = json.load(open(p, encoding="utf-8"))
    U = {}
    txt = {}
    for u in d["units"]:
        U[u["uid"]] = set((x["char"], x["role"]) for x in u["involves"])
        txt[u["uid"]] = u["text"]
    return U, txt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--tsv", default=None, help="默认 units/audit_<a的source>.tsv")
    args = ap.parse_args()
    if args.tsv is None:
        src = json.load(open(args.a, encoding="utf-8")).get("source", "diff")
        args.tsv = f"units/audit_{src}.tsv"
    A, txt = load(args.a); B, _ = load(args.b)
    uids = sorted(set(A) | set(B), key=lambda s: tuple(int(x) for x in s.split("_")))

    ta = sum(len(v) for v in A.values()); tb = sum(len(v) for v in B.values())
    inter = sum(len(A.get(u, set()) & B.get(u, set())) for u in uids)
    union = sum(len(A.get(u, set()) | B.get(u, set())) for u in uids)
    say_a = {u: [c for c, r in A[u] if r == "说"] for u in A}
    say_b = {u: [c for c, r in B[u] if r == "说"] for u in B}

    rows = []
    say_char_dis = say_presence = role_only = char_only = 0
    for u in uids:
        a, b = A.get(u, set()), B.get(u, set())
        if a == b: continue
        sa, sb = set(say_a.get(u, [])), set(say_b.get(u, []))
        if sa and sb and sa != sb: kind = "说话人分歧"; say_char_dis += 1
        elif bool(sa) != bool(sb): kind = "说存在性分歧"; say_presence += 1
        elif set(c for c, _ in a) != set(c for c, _ in b): kind = "涉及角色分歧"; char_only += 1
        else: kind = "说/做/想角色分歧"; role_only += 1
        rows.append((u, kind, sorted(a - b), sorted(b - a), txt.get(u, "")))

    print(f"A={args.a.split('/')[-2]}  B={args.b.split('/')[-2]}")
    print(f"三元组: A={ta} B={tb}  交集={inter} 并集={union}  一致率(交/并)={100*inter/union:.0f}%")
    print(f"说话人: A={sum(len(v) for v in say_a.values())} B={sum(len(v) for v in say_b.values())}")
    print(f"分歧句 {len(rows)} / {len(uids)}  ({100*len(rows)/len(uids):.0f}%)")
    print(f"  说话人分歧 {say_char_dis} | 说存在性分歧 {say_presence} | 涉及角色分歧 {char_only} | 说做想角色分歧 {role_only}")

    with open(args.tsv, "w", encoding="utf-8") as fh:
        fh.write("uid\tkind\tA_only\tB_only\ttext\n")
        for u, k, ao, bo, t in rows:
            fh.write(f"{u}\t{k}\t{ao}\t{bo}\t{t[:50]}\n")
    print(f"审计清单 → {args.tsv}  ({len(rows)} 行)")

if __name__ == "__main__":
    main()
