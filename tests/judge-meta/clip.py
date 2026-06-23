#!/usr/bin/env python3
"""裁剪 + 盲化。每场景内：裁掉动机段(只留回应)、去【】标签与(1)(2)标记、组内打乱(seed固定)。
盲化粒度 = 场景可见(判定必须对场景)，格式+样本号隐藏。
产物：pool.blind.md（判官只读这个）+ keymap.json（隐藏映射，判分前不读）。"""
import json, re, random
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / "probes.json").read_text(encoding="utf-8"))
raw = [json.loads(l) for l in (HERE / "raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

RESP_MARK = re.compile(r"(?:\(\s*2\s*\)|（\s*2\s*）)?\s*[【\[]?\s*(?:赫萝的回应|她的回应|回应)\s*[】\]]?\s*[:：]?")
SEG1_MARK = re.compile(r"[【\[].{0,40}?(?:被触到|真正想要|想要什么).{0,40}?[】\]]")

def clip(content):
    """取回应段：若有回应段标记，取其后；否则全取。再清理残留标签。"""
    t = content.strip()
    # 找最后一个"回应"标记，取其后（动机段在前，回应段在后）
    ms = list(RESP_MARK.finditer(t))
    if ms:
        t = t[ms[-1].end():].strip()
    else:
        # 无回应标记但可能有动机段(1)…(2)：若有(2)取其后
        m2 = re.search(r"\(\s*2\s*\)|（\s*2\s*）", t)
        if m2:
            t = t[m2.end():].strip()
    # 清理：开头残留的【…】小标题、(1)(2)、**bold标题**、行首"赫萝："
    t = re.sub(r"^[\*\s]*", "", t)
    t = SEG1_MARK.sub("", t).strip()
    t = re.sub(r"^[【\[].{0,30}?[】\]]\s*[:：]?\s*", "", t).strip()
    t = re.sub(r"^\(\s*[12]\s*\)|^（\s*[12]\s*）", "", t).strip()
    t = re.sub(r"^\*\*.{0,30}?\*\*\s*", "", t).strip()
    t = re.sub(r"^(赫萝|她)\s*[:：]\s*", "", t).strip()
    return t

by_sc = {}
for r in raw:
    by_sc.setdefault(r["scenario"], []).append(r)

rng = random.Random(20260622)
keymap = {}
md = ["# 盲评池 · judge 只读本文件\n",
      "> 每个场景下列出 9 段“赫萝的回应”（已裁掉任何动机/分析段，去标签）。",
      "> 格式与样本号已隐藏并组内打乱。请对每段按两套量表打分（先整体一遍、再 checklist 一遍）。\n"]

letters = "abcdefghijklmnop"
for sc in P["scenarios"]:
    items = by_sc[sc["id"]]
    rng.shuffle(items)
    md.append(f"\n## {sc['id']} 场景\n")
    md.append(f"**场景**：{sc['scene']}\n")
    for idx, r in enumerate(items):
        bid = f"{sc['id']}-{letters[idx]}"
        keymap[bid] = {"custom_id": r["custom_id"], "format": r["format"], "sample": r["sample"]}
        resp = clip(r["content"])
        md.append(f"\n### [{bid}]\n{resp}\n")

(HERE / "pool.blind.md").write_text("\n".join(md), encoding="utf-8")
(HERE / "keymap.json").write_text(json.dumps(keymap, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote pool.blind.md ({len(keymap)} items) + keymap.json")
