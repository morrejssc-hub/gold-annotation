#!/usr/bin/env python3
"""
health.py —— 建 gold 阶段的"进度体检"(不是评分)。

score.py 评的是"系统准不准"，要等你有 LLM 预测、且 gold 标完才有意义。
建 gold 的过程中你真正想知道的是: 标到哪了? 哪个桶还差多少? 哪些行该优先看?

用法:
  python3 health.py sheet.tsv
"""
import sys, csv, argparse
from collections import Counter, defaultdict

TARGET_PER_BUCKET = 30  # 每桶 >=30 条, 分桶准确率才可信(SE~1/√n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    args = ap.parse_args()
    rows = list(csv.DictReader(open(args.sheet, encoding="utf-8"), delimiter="\t"))
    n = len(rows)
    ck = [r for r in rows if (r.get("checked") or "").strip()]

    print(f"\n总单元: {n}    已核对: {len(ck)} ({len(ck)/n:.0%})    待核对: {n-len(ck)}")

    print("\n── 进度 · 按桶(已核对 / 该桶总数) ──  目标每桶 ≥30")
    by = defaultdict(lambda: [0, 0])
    for r in rows:
        b = r.get("bucket", "")
        by[b][1] += 1
        if (r.get("checked") or "").strip():
            by[b][0] += 1
    for b, (c, t) in sorted(by.items()):
        bar = "█" * min(30, c) + "·" * max(0, min(30, TARGET_PER_BUCKET) - c)
        flag = "  ✓" if c >= TARGET_PER_BUCKET else f"  还差 {TARGET_PER_BUCKET-c}"
        print(f"  {b:<10} {c:>3}/{t:<3} {bar}{flag}")

    print("\n── 按类型 ──")
    for t, c in sorted(Counter(r.get("type", "") for r in rows).items()):
        cc = sum(1 for r in ck if r.get("type") == t)
        print(f"  {t:<10} {cc}/{c} 已核对")

    print("\n── focalizer(视角角色)覆盖 ──")
    foc = Counter((r.get("focalizer") or "∅") for r in rows)
    for k, v in foc.most_common():
        print(f"  {k:<10} {v}")
    if len(foc) > 1:
        print("  ↑ 多个视角值: 若同一场景内不该变, 核对一下(无主语心理单元的归属默认跟它走)")

    print("\n── target(对谁/面对什么)填写率 ──")
    have = sum(1 for r in rows if (r.get("target") or "").strip())
    dlg = [r for r in rows if r.get("type") == "dialogue"]
    dlg_t = sum(1 for r in dlg if (r.get("target") or "").strip())
    print(f"  整体: {have}/{n}    对话 addressee: {dlg_t}/{len(dlg)}")

    print("\n── 优先核对队列(低置信 + 未核对，最该人看) ──")
    pend = [r for r in rows if not (r.get("checked") or "").strip()]
    pend.sort(key=lambda r: float(r.get("guess_conf") or 0))
    for r in pend[:10]:
        print(f"  conf={r.get('guess_conf')}  [{r.get('bucket'):<6}] "
              f"guess={r.get('guess_speaker') or '∅':<4} 「{(r.get('text') or '')[:22]}」")
    if len(pend) > 10:
        print(f"  …还有 {len(pend)-10} 行未核对")

    print()


if __name__ == "__main__":
    main()
