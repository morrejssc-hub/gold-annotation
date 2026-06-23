#!/usr/bin/env python3
"""裁回应段 + 去标签 + 组内打乱 → pool.blind.md(判官只读) + keymap.json(隐藏)。
盲化粒度：场景可见(判分需对场景)，样本号/来源隐藏。"""
import json, re, random
from pathlib import Path

raw = [json.loads(l) for l in Path("raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

# 若 actor 用了"先动机后回应"格式，裁掉动机段只留回应；否则全取。再清残留标签。
RESP = re.compile(r"(?:\(\s*2\s*\)|（\s*2\s*）)?\s*[【\[]?\s*(?:回应|.{0,6}的回应)\s*[】\]]?\s*[:：]?")
def clip(t):
    t = t.strip()
    ms = list(RESP.finditer(t))
    if ms: t = t[ms[-1].end():].strip()
    t = re.sub(r"^[【\[].{0,30}?[】\]]\s*[:：]?\s*", "", t).strip()   # 行首小标题
    t = re.sub(r"^\(\s*[12]\s*\)|^（\s*[12]\s*）", "", t).strip()
    t = re.sub(r"^\*\*.{0,30}?\*\*\s*", "", t).strip()
    return t

by_sc = {}
for r in raw: by_sc.setdefault(r["scene"], []).append(r)

rng = random.Random(20260623)   # 固定 seed 可复现打乱
letters = "abcdefghijklmnop"
keymap, md = {}, ["# 盲评池（判官只读）\n"]
for sc, items in by_sc.items():
    rng.shuffle(items)
    md.append(f"\n## 场景 {sc}\n")
    for idx, r in enumerate(items):
        bid = f"{sc}-{letters[idx]}"
        keymap[bid] = {"custom_id": r["custom_id"], "sample": r["sample"]}
        md.append(f"\n### [{bid}]\n{clip(r['content'])}\n")

Path("pool.blind.md").write_text("\n".join(md), encoding="utf-8")
Path("keymap.json").write_text(json.dumps(keymap, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote pool.blind.md ({len(keymap)} items) + keymap.json")
