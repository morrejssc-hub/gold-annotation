#!/usr/bin/env python3
"""
score.py —— 读核对完的 sheet.tsv，输出"按难度桶的准确率"+"置信度校准曲线"+结构性体检。

评的是 guess_speaker(被测系统) vs gold_speaker(人给的真值)。
只统计 checked 非空的行——没核对过的不算，杜绝"全盘照抄 guess"刷出的假准确率。

用法:
  python3 score.py sheet.tsv
  python3 score.py sheet.tsv --aliases aliases.json
"""
import sys, csv, json, argparse
from collections import defaultdict

def load_canon(path):
    raw = json.load(open(path, encoding="utf-8"))
    m = {}
    for k, v in raw.items():
        if k.startswith("_"): continue
        for name in v: m[name] = k
        m[k] = k
    return m

def norm(name, canon):
    name = (name or "").strip()
    return canon.get(name, name)

def acc(rows, key):
    buckets = defaultdict(lambda: [0, 0])  # key -> [correct, total]
    for r in rows:
        k = r[key]
        buckets[k][1] += 1
        if r["_ok"]: buckets[k][0] += 1
    return buckets

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("--aliases", default="aliases.json")
    args = ap.parse_args()
    canon = load_canon(args.aliases)

    rows = []
    with open(args.sheet, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not r.get("checked", "").strip():        # 只数已核对的
                continue
            if not r.get("gold_speaker", "").strip():    # 真值必须填
                continue
            r["_g"] = norm(r["guess_speaker"], canon)
            r["_t"] = norm(r["gold_speaker"], canon)
            r["_ok"] = (r["_g"] == r["_t"])
            rows.append(r)

    if not rows:
        print("没有已核对的行(checked 列为空)。先在 sheet.tsv 里核对并打 y。")
        return

    n = len(rows); ok = sum(r["_ok"] for r in rows)
    print(f"\n已核对样本: {n}    总准确率: {ok/n:.1%}  ({ok}/{n})")
    se = (ok/n * (1 - ok/n) / n) ** 0.5
    print(f"95% 置信区间 ≈ ±{1.96*se:.1%}   (样本越多越窄, ~1/√n)\n")

    print("── 按难度桶 ──  (n<30 的桶数字不可信, 需补标)")
    for b, (c, t) in sorted(acc(rows, "bucket").items()):
        flag = "  ⚠ 样本不足" if t < 30 else ""
        print(f"  {b:<10} {c/t:5.1%}  ({c}/{t}){flag}")

    print("\n── 按单元类型 ──")
    for b, (c, t) in sorted(acc(rows, "type").items()):
        print(f"  {b:<10} {c/t:5.1%}  ({c}/{t})")

    print("\n── 置信度校准曲线 ──  (用它把 guess_conf 翻译成可信度)")
    bins = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]
    for lo, hi in bins:
        sub = [r for r in rows if lo <= float(r["guess_conf"]) < hi]
        if not sub: continue
        c = sum(r["_ok"] for r in sub)
        print(f"  conf [{lo:.1f},{hi:.1f})  实测准确率 {c/len(sub):5.1%}  (n={len(sub)})")

    print("\n── target(面对什么/对谁说) ──  (选填, 不计入准确率)")
    have = [r for r in rows if r.get("target", "").strip()]
    print(f"  已填 target: {len(have)}/{n} ({len(have)/n:.0%})")
    dlg = [r for r in rows if r["type"] == "dialogue"]
    dlg_t = [r for r in dlg if r.get("target", "").strip()]
    if dlg:
        print(f"  其中对话(addressee 能 condition 语气): {len(dlg_t)}/{len(dlg)}")

    print("\n── 结构性体检(不依赖真值, 可直接跑全量正文) ──")
    unknown = [r for r in rows if r["_g"] and r["_g"] not in canon.values()]
    print(f"  guess 说话人不在别名表: {len(unknown)} 条" + (" ← 多半是错/漏登记" if unknown else ""))
    empty = [r for r in rows if not r["guess_speaker"].strip()]
    print(f"  guess 为空(模型弃权): {len(empty)} 条")

    print("\n── 最该看的错误(按桶) ──")
    for r in [r for r in rows if not r["_ok"]][:8]:
        print(f"  [{r['bucket']}] guess={r['_g'] or '∅'} gold={r['_t']}  「{r['text'][:24]}」")

if __name__ == "__main__":
    main()
