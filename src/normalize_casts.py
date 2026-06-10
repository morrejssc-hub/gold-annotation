#!/usr/bin/env python3
"""Phase1 后处理：跨卷音译归一到官方/种子名。canonical 改官方名，变体进 aka。
用法: python3 normalize_casts.py [--apply]   (默认 dry-run)
"""
import os, json, sys, collections

# 变体 -> 官方/统一 canonical
NORM = {
    "缪莉": "缪里",
    "寇尔": "柯尔",
    "艾莉莎": "艾尔莎",
    "赫罗": "赫萝",
    "鲁华": "鲁瓦德",
    "赛莉姆": "瑟莉姆",
    "塞莉姆": "瑟莉姆",
    "奇曼": "基曼",  # 官方(角川/维基): ルド・キーマン=鲁德·基曼;卷07/08/09 作奇曼
}
# 每个官方名应在 aka 里登记的全部已知变体
AKA_VARIANTS = collections.defaultdict(set)
for v, off in NORM.items():
    AKA_VARIANTS[off].add(v)
    AKA_VARIANTS[off].add(off)

APPLY = "--apply" in sys.argv
CASTS = "casts"
changes = []

for f in sorted(os.listdir(CASTS)):
    if not f.endswith(".json"):
        continue
    p = os.path.join(CASTS, f)
    d = json.load(open(p, encoding="utf-8"))
    dirty = False

    # focalizer 字段归一
    if d.get("focalizer") in NORM:
        old = d["focalizer"]; d["focalizer"] = NORM[old]
        changes.append((f, f"focalizer {old} -> {d['focalizer']}")); dirty = True

    cast = d.get("cast") or []
    for e in cast:
        c = e.get("canonical", "")
        if c in NORM:
            off = NORM[c]
            e["canonical"] = off
            aka = list(e.get("aka") or [])
            # 把官方名 + 旧 canonical 补进 aka（去重保序）
            for name in [off, c]:
                if name not in aka:
                    aka.append(name)
            e["aka"] = aka
            changes.append((f, f"canonical {c} -> {off}")); dirty = True

    if dirty and APPLY:
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"{'[APPLIED]' if APPLY else '[DRY-RUN]'} {len(changes)} 处改动：")
for f, msg in changes:
    print(f"  {f}: {msg}")
