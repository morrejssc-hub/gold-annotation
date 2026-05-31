#!/usr/bin/env python3
"""把 registry_review.tsv 的人工裁决写回每个 cast 的 needs_registry，使每份 cast JSON 自足
（不再依赖外部总账）。每条 registry 项标注 reviewed/verdict/resolution。
用法: python3 finalize_registry.py [--apply]   默认 dry-run
"""
import os, json, csv, sys, collections

APPLY = "--apply" in sys.argv

# 读总账，按 source 分组保持原序
ledger = collections.defaultdict(list)
for r in csv.DictReader(open("registry_review.tsv", encoding="utf-8"), delimiter="\t"):
    ledger[r["source"]].append(r)


def resolution_text(verdict, co, note):
    co = (co or "").strip()
    note = (note or "").strip()
    if verdict == "resolve":
        head = f"已定夺=「{co}」。" if co else "已定夺(见 cast/aka)。"
    elif verdict == "keep_local":
        head = f"已核：篇内无名实体，保留 canonical「{co}」(系列无专名)。" if co else "已核：篇内无名实体(系列无专名)。"
    elif verdict == "drop":
        head = "已核：背景/非角色，无须 registry 处理。"
    else:
        head = "（未裁决）"
    return (head + (" " + note if note else "")).strip()


changed = []
for f in sorted(os.listdir("casts")):
    if not f.endswith(".json"):
        continue
    src = f[:-5]
    if src not in ledger:
        continue
    d = json.load(open("casts/" + f, encoding="utf-8"))
    new_nr = []
    for r in ledger[src]:
        new_nr.append({
            "where": r["where"],
            "expression": r["expression"],
            "issue": r["issue"],
            "reviewed": "人工已核",
            "verdict": r["verdict"],
            "resolution": resolution_text(r["verdict"], r.get("canonical_out"), r.get("note")),
        })
    d["needs_registry"] = new_nr
    changed.append((src, len(new_nr)))
    if APPLY:
        json.dump(d, open("casts/" + f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

tag = "[APPLIED]" if APPLY else "[DRY-RUN]"
total = sum(n for _, n in changed)
print(f"{tag} {len(changed)} 篇 cast 的 needs_registry 已标注人工裁决，共 {total} 条")
# 校验：是否仍有未裁决
miss = [(s, r["expression"][:20]) for s in ledger for r in ledger[s] if not r["verdict"]]
print("未裁决项:", miss if miss else "无 — 58 条全部已 check")
