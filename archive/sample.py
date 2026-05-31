#!/usr/bin/env python3
"""
sample.py —— 从 pool.tsv 取样, 生成待核对的子集。选取以【质量】为主轴。

为什么不按"归属难度(explicit/anaphoric/unmarked)"分层:
  归属对错反正你我都会 check, 不是瓶颈; 真正决定评测集价值的是单元本身有没有"料"——
  有声口的对话、有思考方式的内心。所以:
    1) 先过【质量闸】: 砍掉 ≤min-chars 的短对话和语气词(嗯/是吗), 砍掉琐碎短动作(点点头)。
    2) 按【价值类】分层: 对话 / 心理(自指+推测) / 物理, 配额偏向对话与心理, 压低物理。
    3) 类内按【质量分】排序优先取(长度封顶, 避免一味偏长; 心理加成), 并跨 source 铺开。

  --mode eval (默认): 上述质量优先 + 价值类配额, 建评测集。
  --mode sft       : 同样过质量闸, 再按高置信筛, 建训练种子。

都会跳过 --exclude 里已核对的 (source,scene,sent)。输出列与 pool 一致, checked 留空。

用法:
  python3 sample.py pool.tsv --exclude sheet.tsv \
    --drop-source "黑狼的摇篮,牧羊人与黑骑士,狼与彩虹色的音乐,狼与银色的叹息,狼与将晓之色" \
    > eval_candidates.tsv
  python3 sample.py pool.tsv --quota "对话:120,心理:100,物理:40" --min-chars 8 > eval2.tsv
  python3 sample.py pool.tsv --mode sft --min-conf 0.7 > sft_seed.tsv
"""
import sys, csv, re, argparse
from collections import defaultdict, OrderedDict

CJK = re.compile(r"[一-鿿]")
# 纯语气词/应答(就算够长也无声口价值)。比对的是去掉标点后的整串。
BACKCHANNEL = {"嗯", "啊", "哦", "唔", "欸", "咦", "唉", "呃", "哈", "哼", "嗯嗯", "嗯哼",
               "是吗", "是么", "什么", "怎么", "为什么", "真的", "真的吗", "是吧", "对吧",
               "好", "好的", "好吧", "知道了", "原来如此", "这样啊", "怎么了", "怎么样"}


def cjk_len(t):
    return len(CJK.findall(t or ""))


def bare(t):
    return "".join(CJK.findall(t or ""))


def gate(r, min_chars):
    """质量闸: 太短 / 纯语气词 => 砍。心理单元放宽下限(短内心也可能有料)。"""
    t = r.get("text", "")
    c = cjk_len(t)
    floor = max(4, min_chars - 2) if r.get("bucket", "").startswith("心理") else min_chars
    if c < floor:
        return False
    if r.get("type") == "dialogue" and bare(t) in BACKCHANNEL:
        return False
    return True


def quality(r, core=()):
    """质量分(越大越优先取)。长度封顶 40 避免偏爱超长说明; 心理加成。
    心理的满额加成只给【主角视角】: 罗赫的内心才是 SFT 要学的思考方式;
    配角视角抽出的"心理"是配角的思维, 存疑(见 prepare.py), 只给小加成, 仍略高于纯物理。"""
    s = min(cjk_len(r.get("text", "")), 40)
    b = r.get("bucket", "")
    if b.startswith("心理"):
        if (r.get("focalizer") or "") in core:
            s += 20
            if b == "心理-推测":
                s += 5
        else:
            s += 5
    return s


def vclass(r):
    if r.get("type") == "dialogue":
        return "对话"
    if r.get("bucket", "").startswith("心理"):
        return "心理"
    return "物理"


def read(path):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    with open(path, encoding="utf-8") as f:
        cols = next(csv.reader(f, delimiter="\t"))
    return rows, cols


def spread_pick(rows, n, keyfn):
    """跨 source 轮询取 n 条; 每个 source 内按 keyfn 降序(先取质量高的)。"""
    by_src = OrderedDict()
    for r in sorted(rows, key=lambda r: r.get("source", "")):
        by_src.setdefault(r["source"], []).append(r)
    for s in by_src:
        by_src[s] = sorted(by_src[s], key=keyfn, reverse=True)
    out, srcs, i = [], list(by_src), 0
    while len(out) < n and any(by_src.values()):
        q = by_src[srcs[i % len(srcs)]]
        if q:
            out.append(q.pop(0))
        i += 1
    return out[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pool")
    ap.add_argument("--mode", choices=["eval", "sft"], default="eval")
    ap.add_argument("--quota", default="对话:110,心理:90,物理:40",
                    help="eval: 各价值类配额, 形如 '对话:110,心理:90,物理:40'")
    ap.add_argument("--min-chars", type=int, default=6, help="质量闸: 单元最少汉字数")
    ap.add_argument("--min-conf", type=float, default=0.7, help="sft: 置信度下限")
    ap.add_argument("--max", type=int, default=2000, help="sft: 最多取多少")
    ap.add_argument("--exclude", default=None, help="已核对的 sheet, 跳过其 (source,scene,sent)")
    ap.add_argument("--drop-source", default="", help="逗号分隔的 source, 整篇排除")
    ap.add_argument("--require-focalizer", action="store_true", help="只取 focalizer 非空的行")
    ap.add_argument("--core", default="罗伦斯,赫萝", help="核心声口(按 focalizer 判)")
    ap.add_argument("--core-frac", type=float, default=0.6, help="核心声口最低占比")
    args = ap.parse_args()

    rows, cols = read(args.pool)
    n_raw = len(rows)

    drop = {s.strip() for s in args.drop_source.split(",") if s.strip()}
    if drop:
        rows = [r for r in rows if r.get("source", "") not in drop]
    if args.require_focalizer:
        rows = [r for r in rows if (r.get("focalizer") or "").strip()]

    skip = set()
    if args.exclude:
        ex, _ = read(args.exclude)
        for r in ex:
            if (r.get("checked") or "").strip():
                skip.add((r.get("source", ""), r.get("scene", ""), r.get("sent", "")))
    rows = [r for r in rows
            if (r.get("source", ""), r.get("scene", ""), r.get("sent", "")) not in skip]

    # 质量闸
    n_pre = len(rows)
    rows = [r for r in rows if gate(r, args.min_chars)]
    sys.stderr.write(f"\n质量闸(min-chars={args.min_chars}): {n_pre} -> {len(rows)} "
                     f"(砍掉 {n_pre-len(rows)} 条短/语气词单元)\n")

    core = {c.strip() for c in args.core.split(",") if c.strip()}
    qf = lambda r: quality(r, core)  # 心理满额加成只给主角视角

    if args.mode == "eval":
        quota = {}
        for part in args.quota.split(","):
            k, v = part.split(":")
            quota[k.strip()] = int(v)
        byclass = defaultdict(list)
        for r in rows:
            byclass[vclass(r)].append(r)
        picked = []
        sys.stderr.write("\n建评测集(质量优先 + 价值类配额):\n")
        for cls, q in quota.items():
            got = spread_pick(byclass.get(cls, []), q, qf)
            picked += got
            nsrc = len({r["source"] for r in got})
            lens = sorted(cjk_len(r["text"]) for r in got)
            med = lens[len(lens)//2] if lens else 0
            sys.stderr.write(f"  {cls:<6} 取 {len(got):>3} / 可选 {len(byclass.get(cls, [])):>5}   "
                             f"摊到 {nsrc} 篇   字数中位 {med}\n")

        # 核心声口配比: 罗/赫 至少占 core-frac, 不够就用高质量核心样本替换低质量非核心样本
        is_core = lambda r: (r.get("focalizer") or "") in core
        N = len(picked)
        need = int(args.core_frac * N + 0.999)
        cur = sum(1 for r in picked if is_core(r))
        if cur < need:
            picked_set = {id(r) for r in picked}
            spare_core = sorted(
                (r for r in rows if is_core(r) and id(r) not in picked_set),
                key=qf, reverse=True)
            noncore_in = sorted((r for r in picked if not is_core(r)), key=qf)
            swaps = min(need - cur, len(spare_core), len(noncore_in))
            drop = {id(r) for r in noncore_in[:swaps]}
            picked = [r for r in picked if id(r) not in drop] + spare_core[:swaps]
            sys.stderr.write(f"  核心声口({'/'.join(core)})配比: {cur}/{N} → "
                             f"换入 {swaps} 条核心样本 → {cur+swaps}/{len(picked)} "
                             f"({(cur+swaps)/len(picked):.0%}, 目标 {args.core_frac:.0%})\n")
        else:
            sys.stderr.write(f"  核心声口({'/'.join(core)})配比: {cur}/{N} "
                             f"({cur/N:.0%}) 已达标 {args.core_frac:.0%}\n")
    else:  # sft
        cand = [r for r in rows if _conf(r) >= args.min_conf]
        picked = spread_pick(cand, args.max, qf)
        sys.stderr.write(f"\n建 SFT 种子(conf>={args.min_conf}): {len(picked)} / 合格 {len(cand)}\n")
        bb = defaultdict(int)
        for r in picked:
            bb[vclass(r)] += 1
        for b, c in sorted(bb.items()):
            sys.stderr.write(f"  {b:<6} {c}\n")

    w = csv.DictWriter(sys.stdout, fieldnames=cols, delimiter="\t", extrasaction="ignore")
    w.writeheader()
    for r in picked:
        r["checked"] = ""
        w.writerow(r)
    sys.stderr.write(f"\n共 {len(picked)} 条 (池 {n_raw}) -> stdout。核对完可 merge 进 sheet.tsv。\n")


def _conf(r):
    try:
        return float(r.get("guess_conf") or 0)
    except ValueError:
        return 0.0


if __name__ == "__main__":
    main()
