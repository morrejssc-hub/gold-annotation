#!/usr/bin/env python3
"""
merge.py —— 把"重新生成的表(new)"并进"你已核对的表(old)"，不动你的核对成果。

为什么需要它: 改了抽取器(补召回/加 focalizer/拆桶)后想重跑 prepare.py，
但直接覆盖会毁掉你已 check 的行。merge 只增量更新机器列，保留人工列。

对齐键 = (scene, sent, type, 组内出现序)，不依赖 uid——因为表格软件会把 1-0 存成日期。

合并规则(每个键):
  1) old 已核对(checked 非空)         -> 原样保留 old 行(只补 old 缺的新列, 如 focalizer)
  2) old 未核对 且 new 有             -> 用 new(更新的 guess/bucket/召回),
                                        但把 old 里的人工编辑(gold/target/note)叠回来
  3) 只在 old 有(new 没抽到)          -> 保留 old(可能是你手动拆出来的 a/b 行)
  4) 只在 new 有(以前漏抽的)          -> 加入(这就是召回增益)

用法:
  python3 merge.py sheet.tsv new.tsv > merged.tsv
  # 看一眼 merged.tsv 没问题, 再 mv merged.tsv sheet.tsv
"""
import sys, csv, argparse
from collections import defaultdict


def read_rows(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def keyed(rows):
    """(source,scene,sent,type) -> 该组按顺序的行列表; 组内序号即对齐用的 occ。
       含 source: 跨短篇时 (scene,sent) 会撞车, 必须带上来源才不会错并。"""
    groups = defaultdict(list)
    for r in rows:
        groups[(r.get("source", ""), r.get("scene", ""), r.get("sent", ""), r.get("type", ""))].append(r)
    return groups


def is_checked(r):
    return bool((r.get("checked") or "").strip())


def edited(r):
    """old 未核对, 但人工动过 gold/target/note 也算有价值, 要保留。"""
    g, gu = (r.get("gold_speaker") or "").strip(), (r.get("guess_speaker") or "").strip()
    return (g and g != gu) or (r.get("target") or "").strip() or (r.get("note") or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old", help="你已核对的表")
    ap.add_argument("new", help="重新生成的表(prepare.py 新输出)")
    args = ap.parse_args()

    old_rows, new_rows = read_rows(args.old), read_rows(args.new)
    cols = list(new_rows[0].keys()) if new_rows else list(old_rows[0].keys())

    og, ng = keyed(old_rows), keyed(new_rows)
    allk = list(dict.fromkeys(list(og) + list(ng)))  # 保序并集

    def sortkey(k):
        src, sc, se, ty = k
        ssc = int(sc) if sc.isdigit() else 1 << 30
        sse = int(se) if se.isdigit() else 1 << 30
        return (src, ssc, sse, ty)
    allk.sort(key=sortkey)

    merged = []
    stat = defaultdict(int)
    for k in allk:
        ol, nl = og.get(k, []), ng.get(k, [])
        for i in range(max(len(ol), len(nl))):
            o = ol[i] if i < len(ol) else None
            n = nl[i] if i < len(nl) else None
            if o and is_checked(o):
                row = dict(o)
                if n:  # 补 old 缺/空的新列(如 focalizer)
                    for c in cols:
                        if not (row.get(c) or "").strip() and (n.get(c) or "").strip():
                            row[c] = n[c]
                stat["keep_checked"] += 1
            elif o and n:
                row = dict(n)  # 机器列用新的
                for c in ("gold_speaker", "target", "note", "checked"):
                    if (o.get(c) or "").strip():
                        row[c] = o[c]  # 人工列叠回
                stat["refresh_unchecked"] += 1
            elif o:
                row = dict(o)
                stat["keep_old_only"] += 1
            else:
                row = dict(n)
                stat["add_new"] += 1
            merged.append(row)

    sys.stdout.write("\t".join(cols) + "\n")
    for r in merged:
        sys.stdout.write("\t".join((r.get(c) or "") for c in cols) + "\n")

    f = sys.stderr.write
    f(f"\n合并完成: {len(merged)} 行\n")
    f(f"  保留已核对 (原样):        {stat['keep_checked']}\n")
    f(f"  刷新未核对 (人工编辑叠回): {stat['refresh_unchecked']}\n")
    f(f"  仅 old 有 (保留, 可能是手拆): {stat['keep_old_only']}\n")
    f(f"  新增召回 (以前漏抽):        {stat['add_new']}\n")
    f("  检查无误后:  mv merged.tsv sheet.tsv\n")


if __name__ == "__main__":
    main()
