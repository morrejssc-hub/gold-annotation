#!/usr/bin/env python3
"""units_sample.py —— 抽检单生成器（质检主柱，零模型）。

UNITS.md §5.B：跨模型 diff 只抓「分歧」，抓不到「两臂共谋盲区」（两模型一致地标错）。
共谋盲区只能靠人工抽检兜底——但不能漫无目的地翻全章，要把人力压到**易错桶**里的
**一致句**（两臂 involves 完全相同 → diff 沉默 → 最危险）。本脚本零模型、纯结构，
从 A∩B 一致句里筛出落在难桶的，排成抽检单交人工逐条判。

难桶（共谋盲区高发，参 旅途余白 2_154 教训）:
  多引号 = units_check.multiquote_flag（同句多引号 / 引号+说道：标签）。
  群戏   = 一致 involves 含 ≥3 角色，或含群体/路人实体("-"或 cast playable:false 群体)。
  互换   = 本句有「说」，且相邻一致句也有「说」但说话人不同（双主角轮替边界，易标反）。
  焦点低 = involves 全为 做/low（焦点者推断过标高发：写景误挂焦点者）。

只列**一致句**（A、B 的 (char,role) 集合相同）——分歧句已进 audit，不重复。
输出 units/sample_<篇>.tsv，人工填 verdict 列：
  ok            两臂判对，留。
  char:role:conf;...   改成这个（空串=改为纯写景[]）→ 誊进 fix_<篇>.tsv 喂 units_merge。

用法: python3 units_sample.py 后日谈
      python3 units_sample.py 后日谈 --a units/claude/后日谈.json --b units/gpt/后日谈.json
"""
import json, os, csv, argparse
from units_check import multiquote_flag

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root: 脚本在 src/, 数据在根


def load_units(p):
    d = json.load(open(p, encoding="utf-8"))
    return {u["uid"]: u for u in d["units"]}, [u["uid"] for u in d["units"]]


def keyset(u):
    return frozenset((x["char"], x["role"]) for x in u["involves"])


def load_group_chars(src):
    """cast 里 playable:false / present:false 的群体/路人实体 + "-"。"""
    cast = json.load(open(os.path.join(HERE, "casts", src + ".json"), encoding="utf-8"))
    g = {"-"}
    for c in cast.get("cast", []):
        if c.get("playable") is False or c.get("present") is False:
            g.add(c["canonical"])
    return g


def involves_str(inv):
    return ";".join(f"{x['char']}:{x['role']}:{x.get('conf','high')}" for x in inv) or "[]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--a", default=None)
    ap.add_argument("--b", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--cap", type=int, default=8, help="每桶最多抽样几句（多引号桶不限）")
    args = ap.parse_args()
    src = args.source
    a_path = args.a or os.path.join(HERE, "units", "claude", src + ".json")
    b_path = args.b or os.path.join(HERE, "units", "gpt", src + ".json")
    out_path = args.out or os.path.join(HERE, "units", f"sample_{src}.tsv")

    A, order = load_units(a_path)
    B, _ = load_units(b_path)
    groups = load_group_chars(src)

    # 一致句（含纯写景一致的 []）按句序
    agreed = [uid for uid in order if uid in B and keyset(A[uid]) == keyset(B[uid])]
    agreed_set = set(agreed)

    # 互换：本句有说 + 相邻一致句也有说但说话人不同
    def say_of(uid):
        s = [x["char"] for x in A[uid]["involves"] if x["role"] == "说"]
        return s[0] if s else None

    swap = set()
    for i, uid in enumerate(agreed):
        sp = say_of(uid)
        if not sp:
            continue
        for j in (i - 1, i + 1):
            if 0 <= j < len(agreed):
                sp2 = say_of(agreed[j])
                if sp2 and sp2 != sp:
                    swap.add(uid)

    # 每句归桶
    hits = {}  # uid -> [tags]
    for uid in agreed:
        u = A[uid]
        inv = u["involves"]
        chars = [x["char"] for x in inv]
        tags = []
        if multiquote_flag(u["text"]):
            tags.append("多引号")
        if len(chars) >= 3 or any(c in groups for c in chars):
            tags.append("群戏")
        if uid in swap:
            tags.append("互换")
        if inv and all(x["role"] == "做" and x.get("conf") == "low" for x in inv):
            tags.append("焦点低")
        if tags:
            hits[uid] = tags

    # 按桶等距采样（抽检≠全量审计）：多引号最稀有最高价 → 全取；其余按 cap 等距抽。
    # 一句多桶时归到它命中的最稀有桶，避免重复计数。
    PRIORITY = ["多引号", "群戏", "互换", "焦点低"]
    CAPS = {"多引号": 999, "群戏": args.cap, "互换": args.cap, "焦点低": args.cap}
    by_bucket = {b: [] for b in PRIORITY}
    for uid in agreed:  # 句序
        if uid in hits:
            primary = min(hits[uid], key=PRIORITY.index)
            by_bucket[primary].append(uid)

    picked, dropped = {}, {}
    for b in PRIORITY:
        pool = by_bucket[b]
        cap = CAPS[b]
        if len(pool) <= cap:
            sel = pool
        else:  # 等距步采样，确定性、覆盖全章
            step = len(pool) / cap
            sel = [pool[int(i * step)] for i in range(cap)]
        for uid in sel:
            picked[uid] = hits[uid]
        dropped[b] = len(pool) - len(sel)

    rows = sorted(picked, key=order.index)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["uid", "buckets", "involves(两臂一致)", "verdict(ok/改:involves)", "note", "text"])
        for uid in rows:
            w.writerow([uid, "|".join(picked[uid]), involves_str(A[uid]["involves"]), "", "", A[uid]["text"]])

    from collections import Counter
    bc = Counter(min(t, key=PRIORITY.index) for t in picked.values())
    drop = {b: n for b, n in dropped.items() if n}
    print(f"{src}: 一致句 {len(agreed)}/{len(order)} → 命中难桶 {len(hits)} → 抽检采样 {len(rows)} 句"
          f"（按主桶 {dict(bc)}）" + (f"  ⚠ 采样丢弃 {drop}（cap={args.cap}，调大 --cap 看全量）" if drop else ""))
    print(f"抽检单 → {os.path.relpath(out_path, HERE)}")


if __name__ == "__main__":
    main()
