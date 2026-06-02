#!/usr/bin/env python3
"""
phase2_eval.py —— Phase 2 归属产物的自动校验。

干两件事, 都不靠模型:
  1) 覆盖率: phase2/<篇>.json 的 labels 是否与 dialogue.py 抽出的 uid 完全对齐
     (无遗漏 / 无多余 / 无重复)。
  2) 一致率: 对 eval.tsv 里该篇已核 gold 行, 比对 phase2 的 speaker。
     gold 用的是【视角相对/局部】表层称谓(主人/女子/这女孩…), 所以比对要经 cast
     的 aka+appellations+descriptors 归一: 只要 gold 表层与 phase2 canonical 的任一
     别名相容(相等或互为子串, 去掉描述符里的"(场景1)"等括注), 即算命中。

用法:
  python3 phase2_eval.py phase2/后日谈.json            # 单篇
  python3 phase2_eval.py --all phase2                  # 全量
依赖同目录: dialogue.py, eval.tsv, casts/<篇>.json
"""
import sys, os, re, json, glob, csv, argparse, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def extracted_uids(src_json):
    out = subprocess.run([sys.executable, os.path.join(HERE, "dialogue.py"), src_json],
                         capture_output=True, text=True).stdout.splitlines()
    return [l.split("\t")[0] for l in out[1:] if l.strip()]


def norm(s):
    """去括注、去空白, 用于别名相容判断。"""
    return re.sub(r"[（(].*?[)）]", "", s).strip()


def alias_set(cast, canonical):
    """某 canonical 的全部表层别名(归一后)。"""
    al = set()
    for c in cast.get("cast", []):
        if c.get("canonical") == canonical:
            for k in ("aka", "appellations", "descriptors"):
                for v in c.get(k, []):
                    n = norm(v)
                    if n:
                        al.add(n)
            al.add(canonical)
    return al


def compatible(gold_surface, predicted_canonical, cast):
    """gold 表层称谓 与 phase2 canonical 是否相容。"""
    g = norm(gold_surface)
    if g in ("-", "—", ""):
        return predicted_canonical == "-"
    if g == predicted_canonical:
        return True
    for a in alias_set(cast, predicted_canonical):
        if g == a or g in a or a in g:
            return True
    return False


def gold_rows(source):
    """返回 (checked_gold, unchecked_guess) 两档:
       checked_gold = 人工已核(checked=y)的 (uid,标签,note) —— 真正的一致率分母;
       unchecked_guess = 仅机器猜测未核(checked!=y 但有 gold_speaker) —— 复核候选, 不计入率。"""
    path = os.path.join(HERE, "eval.tsv")
    rows = list(csv.reader(open(path, encoding="utf-8"), delimiter="\t"))
    h = rows[0]
    checked, guess = [], []
    for r in rows[1:]:
        d = dict(zip(h, r))
        if d["source"] != source:
            continue
        g = d.get("gold_speaker", "").strip()
        if not g:
            continue
        rec = (d["uid"], g, d.get("note", ""))
        (checked if d.get("checked") == "y" else guess).append(rec)
    return checked, guess


def eval_one(p2_path):
    p2 = json.load(open(p2_path, encoding="utf-8"))
    source = p2["source"]
    src_json = os.path.join(HERE, "jsons", source + ".json")
    if not os.path.exists(src_json):
        src_json = os.path.join(HERE, "maintext", source + ".json")
    cast = json.load(open(os.path.join(HERE, "casts", source + ".json"), encoding="utf-8"))

    labels = {x["uid"]: x for x in p2["labels"]}
    ext = extracted_uids(src_json)
    se, sl = set(ext), set(labels)
    missing, extra = sorted(se - sl), sorted(sl - se)
    dups = sorted(u for u in sl if [x["uid"] for x in p2["labels"]].count(u) > 1)

    checked, guess = gold_rows(source)
    agree, disagree, no_gold_label = [], [], []
    for uid, gold, note in checked:
        if uid not in labels:
            no_gold_label.append(uid)
            continue
        pred = labels[uid]["speaker"]
        (agree if compatible(gold, pred, cast) else disagree).append((uid, gold, pred, note))

    review = []  # 未核机器猜测 与 phase2 不一致 → 复核候选
    for uid, gv, note in guess:
        if uid in labels:
            pred = labels[uid]["speaker"]
            if not compatible(gv, pred, cast):
                review.append((uid, gv, pred, note))

    return {
        "source": source, "extracted": len(ext), "labeled": len(labels),
        "missing": missing, "extra": extra, "dups": dups,
        "gold_total": len(agree) + len(disagree) + len(no_gold_label),
        "agree": agree, "disagree": disagree, "no_label": no_gold_label,
        "review": review,
    }


def report(r):
    cov_ok = not (r["missing"] or r["extra"] or r["dups"])
    print(f"── {r['source']} ──")
    print(f"  覆盖: 抽取 {r['extracted']} / 标注 {r['labeled']}  "
          + ("✓ 完全对齐" if cov_ok else "✗"))
    if r["missing"]: print(f"    遗漏: {r['missing']}")
    if r["extra"]:   print(f"    多余: {r['extra']}")
    if r["dups"]:    print(f"    重复: {r['dups']}")
    g = r["gold_total"]
    n = len(r["agree"])
    if g:
        print(f"  gold 一致: {n}/{g} = {100*n/g:.0f}%")
    for uid, gold, pred, note in r["disagree"]:
        print(f"    ✗ {uid}: gold={gold!r} phase2={pred!r}" + (f"  [{note}]" if note else ""))
    if r["no_label"]:
        print(f"    (checked gold 行未在 phase2 标注: {r['no_label']})")
    if r["review"]:
        print(f"  复核候选 (未核机器猜测 ≠ phase2, {len(r['review'])} 条):")
        for uid, gv, pred, note in r["review"]:
            print(f"    ? {uid}: 旧猜测={gv!r} phase2={pred!r}" + (f"  [{note}]" if note else ""))
    return cov_ok, n, g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="单个 phase2/*.json, 或配合 --all 给 phase2 目录")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.path, "*.json"))) if args.all else [args.path]

    cov_all, agree_all, gold_all = True, 0, 0
    for f in files:
        r = eval_one(f)
        cov_ok, n, g = report(r)
        cov_all &= cov_ok; agree_all += n; gold_all += g
    if len(files) > 1:
        print(f"\n总计: 覆盖 {'全✓' if cov_all else '有缺口'}; "
              f"gold 一致 {agree_all}/{gold_all} = {100*agree_all/gold_all:.0f}%"
              if gold_all else "")


if __name__ == "__main__":
    main()
