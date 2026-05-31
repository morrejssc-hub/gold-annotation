#!/usr/bin/env python3
"""
pool.py —— 把多篇 json 一次性抽成一个大候选池(pool.tsv)，带 source 列。

覆盖度的第一步: 把所有短篇都过一遍, 汇成一个池子, 再由 sample.py 分层取样。
顺带体检每篇的"角色名覆盖率", 提示 aliases.json 该补哪些角色(别的短篇主角不是罗伦斯)。

用法:
  python3 pool.py ../sw-sft/jsons/*.json > pool.tsv
  python3 pool.py ../sw-sft/jsons/ > pool.tsv          # 给目录也行
"""
import sys, os, json, glob, argparse
from collections import Counter
import prepare  # 复用抽取逻辑(同目录)


def iter_jsons(paths):
    for p in paths:
        if os.path.isdir(p):
            yield from sorted(glob.glob(os.path.join(p, "*.json")))
        else:
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="json 文件或目录")
    ap.add_argument("--aliases", default="aliases.json")
    ap.add_argument("--focalizers", default="focalizers.tsv",
                    help="人标的视角角色表(source->focalizer), 覆盖启发式。")
    ap.add_argument("--no-fid", action="store_true")
    args = ap.parse_args()

    v2c, variants, _ = prepare.load_aliases(args.aliases)
    canon_variants = {}
    for v, c in v2c.items():
        canon_variants.setdefault(c, []).append(v)
    foc_override = prepare.load_focalizers(args.focalizers)

    sys.stdout.write("\t".join(prepare.COLS) + "\n")
    report = []  # (source, n_units, focalizer, named_rate)
    total = 0
    bad = []
    for path in iter_jsons(args.paths):
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            bad.append((os.path.basename(path), str(e)[:60]))
            continue
        src = doc.get("title") or os.path.splitext(os.path.basename(path))[0]
        rows = prepare.extract(doc, v2c, variants, canon_variants,
                               no_fid=args.no_fid, source=src, foc_override=foc_override)
        for r in rows:
            sys.stdout.write("\t".join(r) + "\n")
        total += len(rows)
        # 体检: 这篇的视角角色 + 有多少 guess 命中了别名表(命中率低=别名缺角色)
        foc = rows[0][6] if rows else "∅"
        named = sum(1 for r in rows if r[9] and r[9] in v2c.values())
        rate = named / len(rows) if rows else 0
        report.append((src, len(rows), foc, rate))

    f = sys.stderr.write
    f(f"\n池子: {total} 单元 / {len(report)} 篇\n\n")
    f(f"{'篇名':<22}{'单元':>5}{'视角':>8}{'命中别名率':>10}\n")
    for src, n, foc, rate in report:
        warn = "  ⚠ 别名可能缺角色" if rate < 0.6 else ""
        f(f"{src:<22}{n:>5}{foc:>8}{rate:>9.0%}{warn}\n")
    f("\n命中率低的篇: 多半主角/配角不在 aliases.json, 补全后重跑(focalizer 会更准)。\n")
    if bad:
        f(f"\n⚠ 跳过 {len(bad)} 个坏 json(解析失败):\n")
        for name, err in bad:
            f(f"  {name}: {err}\n")


if __name__ == "__main__":
    main()
