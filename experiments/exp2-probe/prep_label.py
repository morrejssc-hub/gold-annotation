"""把 holdout jsonl 抽成可读的待标注清单（judgement 由人/LLM 读 context 做，本脚本只整理）。

用法: python experiments/exp2-probe/prep_label.py
输出: experiments/exp2-probe/_holdout_to_label.md   （UTF-8，分条，含上文尾部 + gold 反验锚）
"""
import json, ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "rp" / "eval" / "holdout" / "赫萝_番外.jsonl"
OUT = ROOT / "experiments" / "exp2-probe" / "_holdout_to_label.md"

TAIL = 6          # 上文取最后几轮（越靠后越接近开口点，信任档位由临近情境定）
PER_TURN = 140    # 每轮文本截断
GOLD_CAP = 240    # gold 截断


def parse(s):
    """input_left / gold_target 是 Python repr 字符串（单引号），用 literal_eval 解析。"""
    if isinstance(s, (list, dict)):
        return s
    if isinstance(s, str):
        try:
            return ast.literal_eval(s)
        except Exception:
            return s
    return s


def turn_text(t):
    return t.get("text", "") if isinstance(t, dict) else str(t)


def main():
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8")]
    lines = [f"# holdout 待标注清单（N={len(rows)}）\n",
             "标注：在每条 `=> ` 后填 high / low / mid / excl + 半句理由\n"]
    for i, r in enumerate(rows):
        il = parse(r.get("input_left"))
        gt = parse(r.get("gold_target"))
        if isinstance(il, list):
            tail = [x for x in il if isinstance(x, dict)][-TAIL:]
            ctx = "\n    ".join(f"{t.get('uid','')}: {turn_text(t)[:PER_TURN]}" for t in tail)
            nturn = len(il)
        else:
            ctx = str(il)[:PER_TURN * TAIL]
            nturn = "?"
        if isinstance(gt, list):
            gold = " ".join(turn_text(t)[:GOLD_CAP] for t in gt)
        else:
            gold = str(gt)[:GOLD_CAP]
        lines.append(
            f"### [{i}] {r.get('source')} · scene{r.get('scene')} · {r.get('char')} "
            f"· id={r.get('id')} · {nturn}轮\n"
            f"  ctx尾:\n    {ctx}\n"
            f"  gold(反验): {gold}\n"
            f"  => \n"
        )
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {len(rows)} items -> {OUT}")
    print(f"size = {OUT.stat().st_size/1024:.1f} KB")


if __name__ == "__main__":
    main()
