#!/usr/bin/env python3
"""解匿名并按模型统计盲判结果，产出 REPORT 数据。"""
import json
from pathlib import Path
from collections import defaultdict

OUT = Path(__file__).resolve().parent
keymap = json.loads((OUT / "judge_keymap.json").read_text(encoding="utf-8"))
results = json.loads((OUT / "judge_results.json").read_text(encoding="utf-8"))

MODELS = ["qwen3.7-plus", "qwen3.7-max", "deepseek-v4-pro"]
stat = {m: defaultdict(int) for m in MODELS}
stat_prose = {m: [] for m in MODELS}
intrusions = defaultdict(list)   # model -> [(sid, bias, reason)]
fails = defaultdict(list)        # model -> [(sid, reason)]
attach = {m: defaultdict(int) for m in MODELS}

for r in results:
    sid = r["sid"]
    for label, v in r["verdicts"].items():
        m = keymap[sid][label]
        stat[m]["n"] += 1
        attach[m][v["root_attach"]] += 1
        if v["intrusion"]:
            stat[m]["intrusion"] += 1
            intrusions[m].append((sid, v.get("bias", "?"), v["reason"]))
        if v["runtime_fail"]:
            stat[m]["fail"] += 1
            fails[m].append((sid, v["reason"]))
        stat_prose[m].append(v["prose"])

print(f"{'model':18} {'入侵':>6} {'runtime失败':>10} {'文笔均':>7} {'挂上/勉强/挂不上'}")
for m in MODELS:
    n = stat[m]["n"]
    intr = stat[m]["intrusion"]
    fail = stat[m]["fail"]
    pm = sum(stat_prose[m]) / len(stat_prose[m])
    a = attach[m]
    print(f"{m:18} {intr:>3}/{n:<3} {fail:>10} {pm:>7.2f}   "
          f"{a['挂上']}/{a['勉强']}/{a['挂不上']}")

data = {
    "by_model": {m: {
        "n": stat[m]["n"],
        "intrusion": stat[m]["intrusion"],
        "intrusion_rate": round(stat[m]["intrusion"] / stat[m]["n"], 3),
        "runtime_fail": stat[m]["fail"],
        "prose_mean": round(sum(stat_prose[m]) / len(stat_prose[m]), 2),
        "attach": dict(attach[m]),
        "intrusions": intrusions[m],
        "fails": fails[m],
    } for m in MODELS},
}
(OUT / "tally.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("\ntally.json 已写")
