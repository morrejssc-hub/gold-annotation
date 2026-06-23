#!/usr/bin/env python3
"""裁回应段、去标签、打乱 → pool.blind.md (判官只读) + keymap.json (隐藏)。"""
import json, re, random
from pathlib import Path
HERE = Path(__file__).resolve().parent
raw = [json.loads(l) for l in (HERE/"raw.jsonl").read_text().splitlines() if l.strip()]

RESP = re.compile(r"(?:\(\s*2\s*\)|（\s*2\s*）)?\s*[【\[]?\s*(?:赫萝的回应|她的回应|回应)\s*[】\]]?\s*[:：]?")
SEG1 = re.compile(r"[【\[].{0,40}?(?:被触到|真正想要|想要什么).{0,40}?[】\]]")
def clip(t):
    t=t.strip(); ms=list(RESP.finditer(t))
    if ms: t=t[ms[-1].end():].strip()
    else:
        m=re.search(r"\(\s*2\s*\)|（\s*2\s*）",t)
        if m: t=t[m.end():].strip()
    t=re.sub(r"^[\*\s]*","",t); t=SEG1.sub("",t).strip()
    t=re.sub(r"^[【\[].{0,30}?[】\]]\s*[:：]?\s*","",t).strip()
    t=re.sub(r"^\(\s*[12]\s*\)|^（\s*[12]\s*）","",t).strip()
    t=re.sub(r"^\*\*.{0,30}?\*\*\s*","",t).strip()
    t=re.sub(r"^(赫萝|她)\s*[:：]\s*","",t).strip()
    return t

rng=random.Random(20260623); rng.shuffle(raw)
km={}; md=["# S1 样板 · 盲评池（判官只读）\n","> 9 段“赫萝的回应”，已裁动机段、去标签、打乱。\n"]
for i,r in enumerate(raw,1):
    bid=f"A{i}"; km[bid]={"custom_id":r["custom_id"],"format":r["format"],"sample":r["sample"]}
    md.append(f"\n### [{bid}]\n{clip(r['content'])}\n")
(HERE/"pool.blind.md").write_text("\n".join(md),encoding="utf-8")
(HERE/"keymap.json").write_text(json.dumps(km,ensure_ascii=False,indent=1),encoding="utf-8")
print(f"wrote pool.blind.md ({len(km)}) + keymap.json")
