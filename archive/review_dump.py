#!/usr/bin/env python3
"""临时审阅辅助: 把 sheet.tsv 里未核对的行, 按 (source,scene) 分组,
从原 json 拉 ±W 句更宽的上下文打印, 候选句用 ★ 标出(含 uid/类型/桶/guess/quote)。
仅供 claude 一次性审阅用, 不改数据。

用法: python3 review_dump.py [--w 7] [--source 名] [--start 0] [--ngroups 8]
"""
import csv, json, os, re, argparse
from collections import defaultdict, OrderedDict

QUOTE = re.compile(r"[“「]([^”」]*)[”」]")
JSONDIR = "../sw-sft/jsons"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=7)
    ap.add_argument("--source", default=None)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--ngroups", type=int, default=999)
    args = ap.parse_args()

    rows = [r for r in csv.DictReader(open("sheet.tsv", encoding="utf-8"), delimiter="\t")
            if not (r.get("checked") or "").strip()]
    groups = OrderedDict()
    for r in rows:
        groups.setdefault((r["source"], r["scene"]), []).append(r)

    if args.source:
        groups = OrderedDict((k, v) for k, v in groups.items() if k[0] == args.source)

    keys = list(groups)[args.start:args.start + args.ngroups]
    doc_cache = {}
    for (src, scene) in keys:
        cands = groups[(src, scene)]
        path = os.path.join(JSONDIR, src + ".json")
        if src not in doc_cache:
            try:
                doc_cache[src] = json.load(open(path, encoding="utf-8"))
            except Exception as e:
                doc_cache[src] = None
        doc = doc_cache[src]
        sc = None
        if doc:
            for s in doc.get("scenes", []):
                if str(s["id"]) == str(scene):
                    sc = s; break
        print(f"\n{'='*70}\n《{src}》 scene {scene}   候选 {len(cands)} 条")
        if not sc:
            for r in cands:
                print(f"  ★{r['uid']} [{r['type']}/{r['bucket']}] guess={r['guess_speaker']} 「{r['text'][:40]}」")
            continue
        sents = sc["sents"]
        cand_sents = {int(r["sent"]) for r in cands}
        show = set()
        for cs in cand_sents:
            for j in range(max(0, cs - args.w), min(len(sents), cs + args.w + 1)):
                show.add(j)
        bysent = defaultdict(list)
        for r in cands:
            bysent[int(r["sent"])].append(r)
        prev = -2
        for j in sorted(show):
            if j != prev + 1:
                print("   …")
            sid = sents[j]["id"]
            txt = sents[j]["text"]
            star = "★" if sid in cand_sents else " "
            print(f"  {star}[{sid}] {txt}")
            for r in bysent.get(sid, []):
                tgt = f" target={r['target']}" if r.get("target") else ""
                print(f"       └─ {r['uid']} [{r['type']}/{r['bucket']}] "
                      f"guess={r['guess_speaker']}{tgt}  unit「{r['text'][:50]}」")
            prev = j


if __name__ == "__main__":
    main()
