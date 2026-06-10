#!/usr/bin/env python3
"""
dialogue.py —— 机械抽取对话单元(无归属、无分类、无视角)。

任务定位(重定): 大规模 AI 任务是"给定上下文 + 指定对话 -> 判说话人"。
抽取本身是纯机械的标点边界探测, 不进评测、不靠模型。这个脚本只干这一件事:
把每篇 json 里的每条引号台词切出来, 连同上下文窗口, 输出成行。

引号规则:
  - 外层(成对, 各算一条台词): “…”  和  「…」(港台半括号, 本语料没有但留着稳健)。
  - 内层 ‘…’ / 『…』 是台词内部的引用/强调, 属于同一句话, 不单独成条。
    因为外层用 [^“”] / [^「」] 取内容, 内层是不同字形, 天然被吃进内容里。
  - 一段(sent)可含多条台词 -> 加 qidx 0/1/2…, 各自成行。
  - 不成对的孤引号(跨段/笔误)匹配不到, 自动丢弃(会在 stderr 报数)。

输出列(纯归属评测的原料; gold_speaker/difficulty 之后再加):
  uid  source  scene  sent  qidx  dialogue  context
    context = 目标句前 ctx_before、后 ctx_after 句的原文, 目标句用 ► 标出。
    一段多条时, 靠 qidx + dialogue 原文区分是哪条。

用法:
  python3 dialogue.py jsons/两匹狼的婚礼.json > dlg.tsv      # 单篇
  python3 dialogue.py --all jsons > dialogue_all.tsv         # 全量
"""
import sys, os, re, json, glob, argparse

# 外层引号匹配; 内容里允许任何非外层引号字符(于是内层 ‘’/『』 被当作内容)。
# 末两支: 开引号无对应闭引号(源文笔误漏引号 / 跨段说话) => 取到段末。
# 闭引号无开引号(跨段的尾巴, 如 "……") 匹配不到 => 自动丢弃。
OUTER = re.compile(r'“([^“”]*)”|「([^「」]*)」|“([^“”]*)$|「([^「」]*)$')
COLS = ["uid", "source", "scene", "sent", "qidx", "dialogue", "context"]


def utterances(text):
    """返回该段里的台词列表 [(qidx, content), …], 跳过孤引号与内层引号。"""
    out = []
    for m in OUTER.finditer(text):
        content = next(g for g in m.groups() if g is not None)
        content = content.strip()
        if content:
            out.append(content)
    return out


def extract(doc, source, ctx_before=3, ctx_after=2):
    rows, dangling = [], 0
    for sc in doc.get("scenes", []):
        sents = sc["sents"]
        texts = [s["text"] for s in sents]
        for idx, s in enumerate(sents):
            t = s["text"]
            # 孤引号统计(外层开合数不等 => 有跨段/笔误)
            if t.count("“") != t.count("”") or t.count("「") != t.count("」"):
                dangling += 1
            qs = utterances(t)
            if not qs:
                continue
            lo, hi = max(0, idx - ctx_before), min(len(sents), idx + ctx_after + 1)
            ctx = " ‖ ".join(("►" + texts[j] if j == idx else texts[j])
                             for j in range(lo, hi)).replace("\t", " ").replace("\n", " ")
            for qi, content in enumerate(qs):
                suf = chr(ord("a") + qi) if len(qs) > 1 else ""
                uid = f"{sc['id']}_{s['id']}{suf}"
                rows.append([uid, source, str(sc["id"]), str(s["id"]), str(qi),
                             content.replace("\t", " ").replace("\n", " "), ctx])
    return rows, dangling


def load(path):
    return json.load(open(path, encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="单个 json, 或配合 --all 给 jsons 目录")
    ap.add_argument("--all", action="store_true", help="把目录下所有 *.json 全量抽取")
    ap.add_argument("--ctx-before", type=int, default=3)
    ap.add_argument("--ctx-after", type=int, default=2)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.path, "*.json"))) if args.all else [args.path]
    w_cols = "\t".join(COLS)
    sys.stdout.write(w_cols + "\n")
    total, total_dangle, bad = 0, 0, []
    for f in files:
        try:
            doc = load(f)
        except Exception as e:
            bad.append((os.path.basename(f), str(e)))
            continue
        src = doc.get("title") or os.path.splitext(os.path.basename(f))[0]
        rows, dangling = extract(doc, src, args.ctx_before, args.ctx_after)
        for r in rows:
            sys.stdout.write("\t".join(r) + "\n")
        total += len(rows); total_dangle += dangling
        if args.all:
            sys.stderr.write(f"  {src:<20} {len(rows):>4} 条"
                             + (f"  (孤引号段 {dangling})" if dangling else "") + "\n")
    sys.stderr.write(f"\n共 {total} 条对话, 来自 {len(files)-len(bad)} 篇"
                     f"; 孤引号段合计 {total_dangle}\n")
    for name, err in bad:
        sys.stderr.write(f"  ✗ 跳过坏 json: {name} ({err})\n")


if __name__ == "__main__":
    main()
