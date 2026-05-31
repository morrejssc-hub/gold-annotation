#!/usr/bin/env python3
"""
build_eval.py —— 从对话单元建【纯归属评测集】。

任务: 给定 (context, dialogue) -> 判 speaker。本脚本:
  1) 遍历 jsons, 机械抽对话(同 dialogue.py 的引号规则)。
  2) 给每条自动打【难度】(零人工, 只供分桶/采样, 不进模型输入):
       explicit  : 本句叙述里有名字 + 言说动词(“罗伦斯说道”) -> 正则就能解
       anaphoric : 本句/相邻句叙述里有名字, 但没紧挨言说动词
       unmarked  : 光秃秃一句引号, 全靠轮替/上下文推 -> 模型真正的价值所在
  3) 给每条一个启发式 guess_speaker 作 baseline(也让人工是"确认"而非"输入")。
  4) 采样 ~target 条, 故意压低 explicit、加重 unmarked; 跨篇铺开。
  5) 复用上一轮已审的对话 gold(按 source/scene/sent + 台词文本对齐), 直接预填。

输出列: uid source scene sent qidx difficulty dialogue context guess_speaker gold_speaker checked note
  - gold_speaker: 复用到的=上轮真值; 没复用的=暂等于 guess(占位, 你核对时改)。
  - checked 留空; note 标注来源(复用/baseline)。

用法:
  python3 build_eval.py ../sw-sft/jsons --reuse sheet.tsv --target 200 > eval.tsv
"""
import sys, os, re, json, glob, argparse
from collections import defaultdict, OrderedDict, Counter

QUOTE = re.compile(r'“([^“”]*)”|「([^「」]*)」|“([^“”]*)$|「([^「」]*)$')
SPEECH = "说道问答喊叫嚷应呢喃嘟囔嘀咕低语反问反驳附和开口出声回道"
CJK = re.compile(r"[一-鿿]")


def cjk_len(t):
    return len(CJK.findall(t or ""))


def load_aliases(path):
    raw = json.load(open(path, encoding="utf-8"))
    v2c, canon_variants = {}, {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        for name in v:
            v2c[name] = k
        canon_variants[k] = list(v)
    variants = sorted(v2c, key=len, reverse=True)  # 长别名优先
    return v2c, variants, canon_variants


def find_names(text, variants, v2c):
    hits = []
    for v in variants:
        i = text.find(v)
        if i >= 0:
            hits.append((i, v2c[v]))
    hits.sort()
    seen, out = set(), []
    for _, c in hits:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def strip_quotes(t):
    return QUOTE.sub("", t)


def utterances(t):
    out = []
    for m in QUOTE.finditer(t):
        c = next(g for g in m.groups() if g is not None).strip()
        if c:
            out.append(c)
    return out


def classify(narr_here, narr_prev, narr_next, variants, v2c):
    """返回 (difficulty, names_here, names_neigh)。
    explicit = 言说线索紧贴台词: 本句叙述有名字+言说动词, 或前句以"X…说道(：)"引入。
    冒号引入式("青年喊著︰"在前段) 也算 explicit —— 那是最机械可解的。"""
    names_here = find_names(narr_here, variants, v2c)
    speech_here = any(c in SPEECH for c in narr_here)
    names_neigh = find_names(narr_prev + narr_next, variants, v2c)
    # 前句引入式: 含名字 且 句尾(末8字)带言说动词/冒号
    pname = find_names(narr_prev, variants, v2c)
    ptail = narr_prev[-8:]
    leadin = bool(pname) and (any(c in SPEECH for c in ptail) or any(c in "：:︰" for c in ptail))
    if (names_here and speech_here) or leadin:
        return "explicit", names_here, names_neigh
    if names_here or names_neigh:
        return "anaphoric", names_here, names_neigh
    return "unmarked", names_here, names_neigh


def load_reuse(path):
    """上一轮已审对话 gold: {(source,scene,sent,台词归一): gold}。"""
    import csv
    m = {}
    if not path or not os.path.exists(path):
        return m
    for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"):
        if r.get("type") != "dialogue":
            continue
        g = (r.get("gold_speaker") or "").strip()
        if not g:
            continue
        key = (r.get("source", ""), str(r.get("scene", "")), str(r.get("sent", "")),
               "".join(CJK.findall(r.get("text", ""))))
        m[key] = g
    return m


def build_rows(jsons_dir, variants, v2c, reuse):
    rows = []
    for f in sorted(glob.glob(os.path.join(jsons_dir, "*.json"))):
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        src = doc.get("title") or os.path.splitext(os.path.basename(f))[0]
        for sc in doc.get("scenes", []):
            sents = sc["sents"]
            texts = [s["text"] for s in sents]
            last_speaker = None
            for idx, s in enumerate(sents):
                qs = utterances(texts[idx])
                if not qs:
                    continue
                narr_here = strip_quotes(texts[idx])
                narr_prev = strip_quotes(texts[idx - 1]) if idx > 0 else ""
                narr_next = strip_quotes(texts[idx + 1]) if idx + 1 < len(sents) else ""
                diff, names_here, names_neigh = classify(
                    narr_here, narr_prev, narr_next, variants, v2c)
                # baseline 猜测: 有名优先本句首名, 否则邻句名, 否则轮替上一位
                if names_here:
                    guess = names_here[0]
                elif names_neigh:
                    guess = names_neigh[0]
                else:
                    guess = last_speaker or ""
                lo, hi = max(0, idx - 3), min(len(sents), idx + 3)
                ctx = " ‖ ".join(("►" + texts[j] if j == idx else texts[j])
                                 for j in range(lo, hi)).replace("\t", " ").replace("\n", " ")
                for qi, content in enumerate(qs):
                    suf = chr(ord("a") + qi) if len(qs) > 1 else ""
                    key = (src, str(sc["id"]), str(s["id"]), "".join(CJK.findall(content)))
                    gold = reuse.get(key, "")
                    rows.append({
                        "uid": f"{sc['id']}_{s['id']}{suf}", "source": src,
                        "scene": str(sc["id"]), "sent": str(s["id"]), "qidx": str(qi),
                        "difficulty": diff, "dialogue": content.replace("\t", " "),
                        "context": ctx, "guess_speaker": guess,
                        "gold_speaker": gold or guess,
                        "checked": "", "note": "复用上轮" if gold else "",
                        "_reused": bool(gold),
                    })
                if guess:
                    last_speaker = guess
    return rows


def spread_pick(rows, n):
    """跨 source 轮询取 n 条; 同 source 内: 先复用(免标), 再长台词优先。"""
    by_src = OrderedDict()
    for r in sorted(rows, key=lambda r: r["source"]):
        by_src.setdefault(r["source"], []).append(r)
    for s in by_src:
        by_src[s].sort(key=lambda r: (r["_reused"], cjk_len(r["dialogue"])), reverse=True)
    out, srcs, i = [], list(by_src), 0
    while len(out) < n and any(by_src.values()):
        q = by_src[srcs[i % len(srcs)]]
        if q:
            out.append(q.pop(0))
        i += 1
    return out[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsons_dir")
    ap.add_argument("--aliases", default="aliases.json")
    ap.add_argument("--reuse", default="sheet.tsv")
    ap.add_argument("--target", type=int, default=200)
    ap.add_argument("--quota", default="unmarked:100,anaphoric:60,explicit:40",
                    help="各难度桶配额(故意压低 explicit)")
    ap.add_argument("--min-chars", type=int, default=2)
    args = ap.parse_args()

    v2c, variants, _ = load_aliases(args.aliases)
    reuse = load_reuse(args.reuse)
    rows = build_rows(args.jsons_dir, variants, v2c, reuse)

    n_all = len(rows)
    rows = [r for r in rows if cjk_len(r["dialogue"]) >= args.min_chars]
    sys.stderr.write(f"\n全量对话单元 {n_all}, 过滤(>={args.min_chars}字) 后 {len(rows)}\n")
    dist = Counter(r["difficulty"] for r in rows)
    sys.stderr.write(f"难度分布(全量): {dict(dist)}\n")
    sys.stderr.write(f"可复用 gold 命中: {sum(r['_reused'] for r in rows)} 条\n")

    quota = {}
    for part in args.quota.split(","):
        k, v = part.split(":")
        quota[k.strip()] = int(v)
    bybucket = defaultdict(list)
    for r in rows:
        bybucket[r["difficulty"]].append(r)

    picked = []
    sys.stderr.write("\n采样(压低 explicit, 加重 unmarked):\n")
    for b, q in quota.items():
        got = spread_pick(bybucket.get(b, []), q)
        picked += got
        ru = sum(x["_reused"] for x in got)
        nsrc = len({x["source"] for x in got})
        sys.stderr.write(f"  {b:<10} 取 {len(got):>3}/可选 {len(bybucket.get(b, [])):>5}"
                         f"  复用 {ru:>3}  摊 {nsrc} 篇\n")

    cols = ["uid", "source", "scene", "sent", "qidx", "difficulty", "dialogue",
            "context", "guess_speaker", "gold_speaker", "checked", "note"]
    import csv
    w = csv.DictWriter(sys.stdout, fieldnames=cols, delimiter="\t", extrasaction="ignore")
    w.writeheader()
    for r in picked:
        w.writerow(r)
    ru = sum(r["_reused"] for r in picked)
    sys.stderr.write(f"\n共 {len(picked)} 条 -> stdout。其中 {ru} 条已预填 gold(复用), "
                     f"余 {len(picked)-ru} 条待你核对 guess。\n")


if __name__ == "__main__":
    main()
