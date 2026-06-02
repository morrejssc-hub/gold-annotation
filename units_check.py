#!/usr/bin/env python3
"""
units_check.py —— 单份 units 产物自检（结构不变量 + 说层 vs Phase2 回归）。无 AI。

检查:
  1) 覆盖: units 的 uid 集合/顺序 == render_chapter 的全句 uid（不多不少、同序）。
  2) role 域 ⊆ {说,做}; char ∈ cast.canonical ∪ {"-"}。
  3) 每句 role=说 至多 1 个（多于 1 即异常）。
  4) "有引号≠说" 审计: dialogue.py 机械抽出的台词 uid 中, 哪些未标说（招牌/比喻/引述…）。
  5) 说层回归（若有 phase2/<篇>.json）: 把 role=说 投影成 uid→speaker, 与 Phase2 speaker 比。

用法: python3 units_check.py units/claude/旅途余白.json
"""
import json, sys, os, subprocess, argparse

HERE = os.path.dirname(os.path.abspath(__file__))


def render_uids(src_json):
    out = subprocess.run([sys.executable, os.path.join(HERE, "render_chapter.py"), src_json],
                         capture_output=True, text=True).stdout.splitlines()
    allsent = [l.split("│")[0] for l in out if "│" in l]
    dlg = [l.split("\t")[0] for l in out if "\t" in l]
    return allsent, set(dlg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("units")
    args = ap.parse_args()
    d = json.load(open(args.units, encoding="utf-8"))
    src = d["source"]
    src_json = os.path.join(HERE, "jsons", src + ".json")
    if not os.path.exists(src_json):
        src_json = os.path.join(HERE, "maintext", src + ".json")
    cast = json.load(open(os.path.join(HERE, "casts", src + ".json"), encoding="utf-8"))
    canon = set(c["canonical"] for c in cast.get("cast", [])) | {"-"}

    U = d["units"]
    uids = [u["uid"] for u in U]
    allsent, dlg = render_uids(src_json)

    ok = True
    def chk(cond, msg):
        nonlocal ok
        ok &= cond
        print(("  ✓ " if cond else "  ✗ ") + msg)

    print(f"── {src}  ({d.get('model')}, {d.get('schema_version')}) ──")
    chk(uids == allsent, f"覆盖/顺序与全句一致（units={len(uids)} render={len(allsent)}）")
    badrole = sorted({x["role"] for u in U for x in u["involves"]} - {"说", "做"})
    chk(not badrole, f"role 域 ⊆ {{说,做}}（越界 {badrole}）")
    badchar = sorted({x["char"] for u in U for x in u["involves"]} - canon)
    chk(not badchar, f"char ∈ cast∪{{-}}（越界 {badchar[:6]}）")
    multisay = [u["uid"] for u in U if sum(1 for x in u["involves"] if x["role"] == "说") > 1]
    chk(not multisay, f"每句 说≤1（异常 {multisay}）")

    say = {u["uid"]: [x["char"] for x in u["involves"] if x["role"] == "说"] for u in U}
    say = {k: v[0] for k, v in say.items() if v}
    noquote_say = sorted(dlg - set(say))
    print(f"  ‣ 机械台词 {len(dlg)} 中未标说（有引号≠说）{len(noquote_say)} 条: {noquote_say}")

    p2p = os.path.join(HERE, "phase2", src + ".json")
    if os.path.exists(p2p):
        p2 = {x["uid"]: x["speaker"] for x in json.load(open(p2p, encoding="utf-8"))["labels"]}
        inter = set(say) & set(p2)
        dis = [(u, say[u], p2[u]) for u in inter if say[u] != p2[u]]
        print(f"  ‣ 说层 vs Phase2: 交集 {len(inter)} 一致 {len(inter)-len(dis)} ({100*(len(inter)-len(dis))/max(1,len(inter)):.0f}%)")
        for u, a, b in sorted(dis):
            print(f"      ≠ {u}: units={a!r} phase2={b!r}")
    print("结果:", "OK" if ok else "有问题")


if __name__ == "__main__":
    main()
