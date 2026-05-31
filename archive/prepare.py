#!/usr/bin/env python3
"""
prepare.py —— 把一章 json 抽成"待核对的归属标注表"(TSV，可直接用表格软件打开)。

输入: sw-sft/jsons/*.json (结构: {title, scenes:[{id, sents:[{id,label,text}]}]})
输出: sheet.tsv —— 每行一个待归属单元(对话/动作)，机器已预填一个 guess，你只需核对。

设计要点:
  - 不从零标注。机器先用启发式给出 guess_speaker + 置信度 + 难度桶 + focalizer，
    人只在 guess 错的行改 gold_speaker，并在 checked 列打个 y 表示"已核对"。
    => 把标注从"逐条输入"变成"逐条确认"，这是省力的核心。
  - guess 这一列代表"被评测的系统"。要评测你的 LLM prompt 时，
    用 LLM 的预测覆盖 guess 列(见 --llm 占位)，gold 列始终是人给的真值。
  - 召回: 无主语的心理/言说续句(自由间接引语 FID)也抽出来——这是"思考方式"最值钱的料，
    宁可多抽一点环境噪声(低置信，你删)，也不漏掉无主语的内心描写。

uid 用下划线 (1_0 / 1_8a)，避免表格软件把 "1-0" 自动识别成日期。
一句拆多个单元时加后缀 a/b/c；score/merge 都按 (scene,sent) 对齐，不依赖 uid。

用法:
  python3 prepare.py ../sw-sft/jsons/狼与将晓之色.json > sheet.tsv
"""
import sys, os, json, re, argparse

QUOTE = re.compile(r"[“「]([^”」]*)[”」]")           # 对话: “...” 或 「...」
SPEECH = "说道问答喊叫嚷应叹呢喃嘟囔嘀咕低语反问反驳附和开口出声回道"  # 言说类动词字
PRONOUN = re.compile(r"[他她它]")
CORE = {"罗伦斯", "赫萝"}  # 主角。非主角视角抽出的"心理"是配角的思维, 对 SFT(学罗赫声口/思考)价值低, 故存疑。

# 心理/认知线索(全集): 出现即把动作单元判为"心理"
MENTAL_CUES = ["想", "觉得", "认为", "盘算", "犹豫", "明白", "疑", "回想", "思",
               "打算", "期待", "担心", "纳闷", "好奇", "琢磨", "寻思", "念头",
               "心里", "暗自", "揣", "回忆", "察觉", "意识到", "感到", "感觉",
               "不安", "担忧", "在意", "困惑", "不解", "感慨", "情绪", "心情"]
# 强认知线索(子集): 用于"无主语句是否值得抽成心理单元"——比全集严，少抓环境噪声
MENTAL_STRONG = ["想", "觉得", "认为", "盘算", "犹豫", "纳闷", "揣", "察觉",
                 "意识到", "期待", "担心", "回想", "回忆", "明白", "念头"]
# 推测/认识情态标记: 句子带这些 + 主语是【别人】=> 多半是视角角色在揣度别人(FID theory-of-mind)。
# 故意不含明喻词(像/像是/仿佛/好像)——那是比喻, 不是推测("像城里少女般耸肩"是真动作)。
EPISTEMIC = ["似乎", "也许", "大概", "恐怕", "想必", "八成", "约莫", "估计",
             "兴许", "莫非", "看上去", "看起来", "听起来", "多半", "约摸"]


def has(text, cues):
    return any(c in text for c in cues)


def load_aliases(path):
    raw = json.load(open(path, encoding="utf-8"))
    variant2canon, canon = {}, []
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        canon.append(k)
        for name in v:
            variant2canon[name] = k
    variants = sorted(variant2canon, key=len, reverse=True)  # 长别名优先
    return variant2canon, variants, canon


def find_names(text, variants, variant2canon):
    """返回文中出现的 canonical 名字，按出现位置排序、去重保序。"""
    hits = []
    for v in variants:
        i = text.find(v)
        if i >= 0:
            hits.append((i, variant2canon[v]))
    hits.sort()
    seen, out = set(), []
    for _, c in hits:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def near_speech(text, name_variants):
    """该 name 是否紧挨言说动词(名字后 6 字内出现言说动词字)。"""
    for v in name_variants:
        i = text.find(v)
        if i >= 0:
            tail = text[i + len(v): i + len(v) + 6]
            if any(c in SPEECH for c in tail):
                return True
    return False


# 心理单元亚型(你核对时定准):
#   心理-自指 = 角色自己的内心(默认)；
#   心理-推测 = 视角角色揣度【别人】的心思(theory-of-mind, target=他人)。
# 注意: "推测"只从高精度的 EPISTEMIC 路径产生(情态标记+别人作主语)。
# 不靠"句中另有人名"来判——那会把"罗伦斯叙述赫萝的状态"误标成推测、并配错 target。


def scene_focalizer(sents, variants, variant2canon):
    """视角角色启发式: 全场叙述(抠掉引号)里出现最多的角色名。
       近距三人称里通常锁定一人(SW 多为罗伦斯, 但短篇主角会变——故按篇自适应)。
    """
    from collections import Counter
    cnt = Counter()
    for s in sents:
        narr = QUOTE.sub("", s["text"])
        for n in find_names(narr, variants, variant2canon):
            cnt[n] += 1
    return cnt.most_common(1)[0][0] if cnt else ""


# 列序(source 跟在 uid 后, 标明出自哪一篇——做覆盖度/分文风统计用)
COLS = ["uid", "source", "scene", "sent", "type", "bucket", "focalizer",
        "context", "text", "guess_speaker", "guess_conf",
        "gold_speaker", "target", "checked", "note"]


def load_focalizers(path):
    """读人填的 focalizers.tsv -> {source: focalizer}; 只取填了 focalizer 列的。"""
    import csv
    m = {}
    if not path or not os.path.exists(path):
        return m
    for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"):
        f = (r.get("focalizer") or "").strip()
        if f:
            m[r["source"]] = f
    return m


def extract(doc, variant2canon, variants, canon_variants,
            ctx_before=3, ctx_after=2, no_fid=False, source="", foc_override=None):
    """把一篇 doc 抽成数据行(不含表头)。可被 pool.py 复用。
       foc_override: 人标的视角角色(优先于启发式); 第一人称'我'叙述也会归到它。"""
    out = []
    forced = (foc_override or {}).get(source)
    for sc in doc.get("scenes", []):
        sents = sc["sents"]
        texts = [s["text"] for s in sents]
        foc = forced or scene_focalizer(sents, variants, variant2canon)
        last_speaker = None  # 无标签轮替的"上一位说话人"

        for idx, s in enumerate(sents):
            text = s["text"]
            ctx_lo = max(0, idx - ctx_before)
            ctx_hi = min(len(sents), idx + ctx_after + 1)
            ctx = " ‖ ".join(
                ("►" + texts[j] if j == idx else texts[j]) for j in range(ctx_lo, ctx_hi)
            ).replace("\t", " ")

            quotes = QUOTE.findall(text)
            host_names = find_names(text, variants, variant2canon)      # 全句(动作单元用)
            narration = QUOTE.sub("", text)                              # 抠掉引号, 只剩叙述
            narr_names = find_names(narration, variants, variant2canon)  # 叙述里的名字(对话归属用)

            units = []  # (suffix, type, bucket, guess, conf, text, target)

            if quotes:  # ---- 对话单元 ----
                for qi, q in enumerate(quotes):
                    nv = sum([canon_variants[n] for n in narr_names], [])
                    if narr_names and near_speech(narration, nv):
                        bucket, guess, conf = "explicit", narr_names[0], 0.90
                    elif narr_names:
                        bucket, guess, conf = "anaphoric", narr_names[0], 0.70
                    else:
                        neigh = ""
                        if idx + 1 < len(texts): neigh += QUOTE.sub("", texts[idx + 1])
                        if idx - 1 >= 0:         neigh += QUOTE.sub("", texts[idx - 1])
                        nn = find_names(neigh, variants, variant2canon)
                        if nn:
                            bucket, guess, conf = "anaphoric", nn[0], 0.55
                        else:
                            bucket, guess, conf = "unmarked", (last_speaker or foc), 0.40
                    last_speaker = guess or last_speaker
                    suf = chr(ord("a") + qi) if len(quotes) > 1 else ""
                    units.append((suf, "dialogue", bucket, guess, conf, q, ""))

            elif host_names or PRONOUN.search(text):  # ---- 动作单元(有名字/代词) ----
                others = [n for n in host_names if n != foc]
                if has(text, EPISTEMIC) and others:
                    # 情态标记 + 别人作主语 => 视角角色在【推测】别人(FID theory-of-mind)。
                    # 思考者=视角角色, target=被推测者; 这是"思考方式"最值钱的料, 低置信待你核。
                    bucket, guess, conf, tgt = "心理-推测", foc, 0.40, others[0]
                else:
                    # 叙述里的动作/代词默认归【视角角色】(近距三人称强先验),
                    # 不用 last_speaker——那是对话轮替信号, 会把旁白错配给上一位说话人。
                    guess = host_names[0] if host_names else foc
                    conf = 0.55 if host_names else 0.30
                    bucket = "心理-自指" if has(text, MENTAL_CUES) else "物理"
                    tgt = ""
                units.append(("", "action", bucket, guess, conf, text, tgt))

            elif not no_fid:  # ---- 无主语召回: FID 内心 / 言说续句 ----
                if has(text, MENTAL_STRONG):
                    units.append(("", "action", "心理-自指", foc, 0.35, text, ""))
                elif has(text, SPEECH):
                    units.append(("", "action", "物理", foc, 0.30, text, ""))
                # 否则: 纯环境/格言, 丢弃

            for suf, typ, bucket, guess, conf, utext, tgt in units:
                note = ""
                # 非主角视角的心理: 是配角的思维(不是罗赫), 抽取也更暧昧 => 压低置信 + 标记存疑。
                # 对话不受此限: 配角视角篇里引号台词仍可能是罗赫说的, 价值照旧(说话人你核对时定)。
                if bucket.startswith("心理") and foc not in CORE:
                    conf *= 0.7
                    note = "非主角视角心理:存疑"
                uid = f"{sc['id']}_{s['id']}{suf}"
                out.append([uid, source, str(sc["id"]), str(s["id"]), typ, bucket, foc,
                            ctx, utext.replace("\t", " "), guess, f"{conf:.2f}",
                            guess, tgt, "", note])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter_json")
    ap.add_argument("--aliases", default="aliases.json")
    ap.add_argument("--focalizers", default="focalizers.tsv",
                    help="人标的视角角色表(source->focalizer), 覆盖启发式。")
    ap.add_argument("--ctx-before", type=int, default=3)
    ap.add_argument("--ctx-after", type=int, default=2)
    ap.add_argument("--no-fid", action="store_true",
                    help="关闭无主语心理/言说续句的召回(只抽有名字/代词的句子)。")
    ap.add_argument("--source", default=None, help="source 列值, 默认取 doc title / 文件名。")
    ap.add_argument("--llm", action="store_true",
                    help="(占位) 用 LLM 预测覆盖 guess 列。需自行接入 OpenAI 兼容接口。")
    args = ap.parse_args()

    variant2canon, variants, _ = load_aliases(args.aliases)
    canon_variants = {}  # canonical -> [variants]
    for v, c in variant2canon.items():
        canon_variants.setdefault(c, []).append(v)

    doc = json.load(open(args.chapter_json, encoding="utf-8"))
    src = args.source or doc.get("title") or os.path.splitext(os.path.basename(args.chapter_json))[0]
    foc_override = load_focalizers(args.focalizers)
    rows = extract(doc, variant2canon, variants, canon_variants,
                   args.ctx_before, args.ctx_after, args.no_fid, src, foc_override)
    sys.stdout.write("\t".join(COLS) + "\n")
    sys.stdout.write("\n".join("\t".join(r) for r in rows) + "\n")


if __name__ == "__main__":
    main()
