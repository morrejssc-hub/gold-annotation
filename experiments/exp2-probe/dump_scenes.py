"""dump 指定 (卷, scene) 的全部句子，供人工挑高信任锚 uid。
用法: python experiments/exp2-probe/dump_scenes.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 从 subagent 排除说明里点名的「赫萝对罗伦斯独处/卸防」高信任候选场景
TARGETS = {1: [16, 17], 2: [28], 5: [13, 17, 18, 20, 30]}

out = []
for vol, sids in TARGETS.items():
    j = json.loads((ROOT / "maintext" / f"卷{vol:02d}.json").read_text(encoding="utf-8"))
    smap = {s["id"]: s for s in j["scenes"]}
    for sid in sids:
        sc = smap.get(sid)
        if not sc:
            out.append(f"\n### 卷{vol:02d} scene{sid} —— 不存在")
            continue
        out.append(f"\n### 卷{vol:02d} scene{sid}（共 {len(sc['sents'])} 句）")
        for st in sc["sents"]:
            out.append(f"{sid}_{st['id']}: {st['text'][:130]}")

OUT = ROOT / "experiments" / "exp2-probe" / "_highscene_dump.md"
OUT.write_text("\n".join(out), encoding="utf-8")
print(f"wrote -> {OUT}  ({OUT.stat().st_size/1024:.1f} KB)")
