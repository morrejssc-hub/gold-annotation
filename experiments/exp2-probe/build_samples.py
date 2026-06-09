"""合成 exp2 pilot 对比样本集 samples.jsonl。
- 低信任 6（subagent 从卷01/02/03 捞，赫萝直面对手/商人 + 有台词）
- 高信任 6（人工从卷01/05 独处卸防场景定，含卷5「好害怕→温柔」金样本）
- 每条从 maintext json 按 (scene,holo_sent) 提取「赫萝开口前的连续原文上文」= 探针 input
- 带全套负控制(placebo)列：tone / third_person / has_wine_wheat_trade / vol / 上文长度

用法: python experiments/exp2-probe/build_samples.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CTX_SENTS = 10  # 取赫萝开口前最后 N 句作为上文

# (id, vol, scene, holo_sent, trust, tone, third_person, wine_wheat_trade, interlocutor, note)
SAMPLES = [
    # ---- 低信任：赫萝直面对手/商人，藏到底+识破挡回 ----
    ("lo_v2s5",  2,  5, 68, "low", "冷硬", True,  True,  "拉多培隆老板", "装弱诱敌→当场揭破诈骗"),
    ("lo_v3s18", 3, 18, 31, "low", "冷硬", True,  False, "马克(套情报)", "识破暗讽+不带笑意威慑"),
    ("lo_v2s32", 2, 32, 46, "low", "中性", True,  False, "雷玛里欧",      "识破内情施压挑衅"),
    ("lo_v1s18", 1, 18, 84, "low", "中性", True,  False, "米隆鉴定员",    "抬价话术操盘、维持上位"),
    ("lo_v1s19", 1, 19, 58, "low", "平静", False, True,  "酒吧女店员",    "冷静识破谎言、不动声色"),
    ("lo_v3s17", 3, 17, 11, "low", "平静", True,  False, "马克(探问关系)","假修女姿态滴水不漏挡回"),
    # ---- 高信任：对罗伦斯独处卸防，漏真情/亲密 ----
    ("hi_v5s30", 5, 30, 236, "high", "柔软", False, True,  "罗伦斯", "『咱很害怕…因为汝的…温柔』金样本"),
    ("hi_v5s17", 5, 17, 96,  "high", "柔软", False, False, "罗伦斯", "『咱害怕的就是这种事情』漏真情"),
    ("hi_v5s13", 5, 13, 75,  "high", "中性", False, False, "罗伦斯", "嫉妒打闹卸防"),
    ("hi_v5s20", 5, 20, 143, "high", "中性", False, False, "罗伦斯", "『咱不是汝的伙伴吗』表露信赖"),
    ("hi_v1s16", 1, 16, 91,  "high", "平静", False, False, "罗伦斯", "星空下『汝跟咱活着的世界大不相同』寂寞"),
    ("hi_v1s17", 1, 17, 43,  "high", "平静", False, False, "罗伦斯", "『就算那些家伙看到咱也不会察觉是吧』渴望被察觉"),
]

_scene_cache = {}
def load_scene(vol, scene):
    key = (vol, scene)
    if key not in _scene_cache:
        j = json.loads((ROOT / "maintext" / f"卷{vol:02d}.json").read_text(encoding="utf-8"))
        _scene_cache[key] = {s["id"]: s for s in j["scenes"]}
    sc = _scene_cache[key].get(scene)
    if sc is None:
        raise SystemExit(f"卷{vol:02d} 无 scene {scene}")
    return sc

out = []
for sid, vol, scene, holo, trust, tone, third, wwt, who, note in SAMPLES:
    sc = load_scene(vol, scene)
    sents = sc["sents"]
    ctx_sents = [t for t in sents if t["id"] < holo][-CTX_SENTS:]
    holo_t = next((t for t in sents if t["id"] == holo), None)
    if holo_t is None:
        print(f"  !! {sid}: scene{scene} 无 sent {holo}")
        continue
    context = "".join(t["text"] for t in ctx_sents)
    out.append({
        "id": sid, "trust": trust,
        "source": f"卷{vol:02d}", "vol": vol, "scene": scene,
        "holo_uid": f"{scene}_{holo}", "context": context,
        "holo_turn": holo_t["text"],
        "interlocutor": who, "tone": tone,
        "third_person": third, "has_wine_wheat_trade": wwt,
        "n_ctx_sents": len(ctx_sents), "n_ctx_chars": len(context),
        "note": note,
    })

OUT = ROOT / "experiments" / "exp2-probe" / "samples.jsonl"
with OUT.open("w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"wrote {len(out)} samples -> {OUT}\n")
print("trust       :", dict(Counter(r["trust"] for r in out)))
print("tone        :", dict(Counter(r["tone"] for r in out)))
print("third_person:", dict(Counter((r["trust"], r["third_person"]) for r in out)))
print("vol         :", dict(Counter((r["trust"], r["vol"]) for r in out)))
print("ctx_chars   : min={} max={} mean={:.0f}".format(
    min(r["n_ctx_chars"] for r in out), max(r["n_ctx_chars"] for r in out),
    sum(r["n_ctx_chars"] for r in out) / len(out)))
print("\n--- 抽检每条 holo_turn 是否真是赫萝台词 ---")
for r in out:
    print(f"[{r['trust'][:2]}] {r['id']:10s} {r['holo_uid']:8s} | {r['holo_turn'][:48]}")
