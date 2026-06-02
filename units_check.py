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
import json, sys, os, re, subprocess, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
Q_OPEN = "“"
# 引出下一句发言的说话标签（…说：/…道：/…问道：），出现在含引号的句子里 = 机械台词键定易错
SAY_TAG = re.compile(r"[说道喊嚷问答叫嚷骂](?:道)?[：:]\s*$|[说道喊嚷问答叫嚷骂](?:道)?[：:]“")


def multiquote_flag(text):
    """同句多引号/「引号+说道：标签」——共谋盲区高发桶（如 2_154 唔唔唔 + …感慨地说：）。"""
    nq = text.count(Q_OPEN)
    if nq >= 2:
        return "多引号同句"
    if nq >= 1 and SAY_TAG.search(text):
        return "引号+说道：标签"
    return None


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

    # 抽检预筛（零模型、不依赖 phase2）：同句多引号桶 → 共谋盲区高发，捞给人工抽检（§5.B.3）
    flagged = [(u["uid"], multiquote_flag(u["text"]),
               sorted({(x["char"], x["role"]) for x in u["involves"]}))
              for u in U if multiquote_flag(u["text"])]
    print(f"  ‣ 抽检预筛·同句多引号 {len(flagged)} 句（待人工抽检；非错，是共谋盲区高发桶）:")
    for uid, why, inv in flagged:
        print(f"      ⚑ {uid} [{why}] {inv}")

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
