#!/usr/bin/env python3
"""
focalizers.py —— 生成"每篇视角角色"待填表 focalizers.tsv。

视角角色(focalizer)单靠"出现最多的名字"判不准: 第一人称短篇里, 叙述者"我"才是视角,
但他的名字在叙述里反而少出现(寇尔叙述的《两匹狼的婚礼》、牧羊犬叙述的《后日谈》)。
所以这一项交给人标: 本脚本把线索摆出来(是否第一人称、我/咱频次、高频名), 你只填 focalizer 一列。

填好后, prepare.py/pool.py 用 --focalizers focalizers.tsv 覆盖启发式, 再重抽就准了。

用法: python3 focalizers.py > focalizers.tsv
"""
import sys, os, json, glob, re
import prepare

JSONDIR = "../sw-sft/jsons"
QUOTE = prepare.QUOTE
FP = re.compile(r"[我咱]")  # 第一人称


def main():
    v2c, variants, _ = prepare.load_aliases("aliases.json")
    cols = ["source", "sents", "narr_我", "pov", "top_names", "focalizer_guess",
            "focalizer", "note"]
    print("\t".join(cols))
    for path in sorted(glob.glob(os.path.join(JSONDIR, "*.json"))):
        src = os.path.splitext(os.path.basename(path))[0]
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except Exception:
            print("\t".join([src, "?", "?", "坏json", "", "", "", "解析失败"]))
            continue
        sents = [s for sc in doc.get("scenes", []) for s in sc["sents"]]
        from collections import Counter
        names, fp_narr, nchar = Counter(), 0, 0
        for s in sents:
            narr = QUOTE.sub("", s["text"])
            nchar += len(narr)
            fp_narr += len(FP.findall(narr))
            for n in prepare.find_names(narr, variants, v2c):
                names[n] += 1
        top = names.most_common(3)
        topname = top[0][0] if top else ""
        top_str = " ".join(f"{n}:{c}" for n, c in top)
        # 第一人称判据: 叙述里"我/咱"密度高, 且高于头号人名出现次数 => 多半第一人称
        top_cnt = top[0][1] if top else 0
        first = fp_narr > top_cnt and fp_narr > 15
        pov = "第一人称?" if first else "第三人称"
        # 干净的第三人称: 预填 focalizer=头号名(你只需确认/改); 第一人称与无名篇留空逼你定。
        offcast = (not top) or top_cnt < 5
        prefill = "" if (first or offcast) else topname
        if first:
            note = "★第一人称: 叙述者≠高频名, 视角是'我'(请填其角色名)"
        elif offcast:
            note = "★别名没覆盖此篇角色(异类短篇): 补 aliases 或本轮 drop"
        elif top and len(top) > 1 and top[1][1] >= top_cnt * 0.85:
            note = f"两视角接近({top_str}): 确认主视角"
        else:
            note = ""
        print("\t".join([src, str(len(sents)), str(fp_narr), pov, top_str,
                          topname, prefill, note]))


if __name__ == "__main__":
    main()
